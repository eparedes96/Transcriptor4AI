from __future__ import annotations

"""
Background Worker Threads for GUI Operations.

Orchestrates long-running tasks such as pipeline execution, update checks,
remote pricing synchronization, and remote telemetry submission. Prevents 
the graphical user interface from freezing by delegating CPU-bound and 
I/O-bound operations to separate daemon threads while maintaining 
communication via thread-safe callbacks.
"""

import logging
import os
import threading
import zipfile
from typing import Any, Callable, Dict, Optional, Tuple

from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.domain import constants as const
from transcriptor4ai.infra import network

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PIPELINE EXECUTION WORKERS
# -----------------------------------------------------------------------------

def run_pipeline_task(
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        on_complete: Callable[[Any], None],
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """
    Execute the transcription pipeline in a dedicated background thread.

    Manages the full transcription lifecycle. Checks for cancellation signals
    before and after execution to ensure responsive thread termination.

    Args:
        config: Full configuration dictionary for the session.
        overwrite: Permission to replace existing output files.
        dry_run: Flag to enable simulation mode.
        on_complete: Callback function to marshal results back to the GUI.
        cancellation_event: Event flag used to abort execution.
    """
    try:
        if cancellation_event and cancellation_event.is_set():
            logger.info("Pipeline Thread: Aborted by user before start.")
            return

        # Trigger core engine orchestration
        result = run_pipeline(
            config,
            overwrite=overwrite,
            dry_run=dry_run,
            cancellation_event=cancellation_event
        )

        if cancellation_event and cancellation_event.is_set():
            logger.info(
                "Pipeline Thread: Execution completed but results discarded due to cancellation."
            )
            return

        # Synchronize results with the UI controller
        on_complete(result)

    except Exception as e:
        logger.critical(f"Pipeline Thread: Critical failure detected: {e}", exc_info=True)
        on_complete(e)


# -----------------------------------------------------------------------------
# NETWORK AND UPDATE WORKERS
# -----------------------------------------------------------------------------

def check_updates_task(
        on_complete: Callable[[Any, bool], None],
        is_manual: bool = False
) -> None:
    """
    Execute a remote release synchronization task.

    Args:
        on_complete: Callback to handle release metadata.
        is_manual: Whether the check was explicitly triggered by the user.
    """
    try:
        res = network.check_for_updates(const.CURRENT_CONFIG_VERSION)
        on_complete(res, is_manual)
    except Exception as e:
        logger.error(f"Update Task: Check failed during network call: {e}")
        on_complete({"has_update": False, "error": str(e)}, is_manual)

def run_pricing_update_task(
        on_complete: Callable[[Optional[Dict[str, Any]]], None]
) -> None:
    """
    Synchronize LLM pricing data from the remote repository.

    Args:
        on_complete: Callback to handle the retrieved pricing dictionary.
    """
    try:
        logger.debug("Pricing Task: Initiating remote sync...")
        pricing_data = network.fetch_pricing_data(const.PRICING_DATA_URL)
        on_complete(pricing_data)
    except Exception as e:
        logger.error(f"Pricing Task: Sync failed: {e}")
        on_complete(None)

def download_update_task(
        binary_url: str,
        dest_path: str,
        on_progress: Callable[[float], None],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Acquire and unpack a remote binary package in the background.

    Handles the full binary acquisition lifecycle, including streaming
    download, progress reporting, and ZIP extraction for portable bundles.

    Args:
        binary_url: Remote source URL.
        dest_path: Local target path for binary staging.
        on_progress: Callback to update UI progress bars (0.0 - 100.0).
        on_complete: Callback to report final task status.
    """
    success, msg = network.download_binary_stream(binary_url, dest_path, on_progress)

    # Secondary lifecycle: Extraction if the asset is a compressed archive
    if success and dest_path.lower().endswith(".zip"):
        try:
            logger.info(f"Update Task: Unpacking compressed archive: {dest_path}")
            base_dir = os.path.dirname(dest_path)

            # Resolve the executable artifact inside the archive
            with zipfile.ZipFile(dest_path, 'r') as zf:
                exe_files = [f for f in zf.namelist() if f.lower().endswith(".exe")]
                if not exe_files:
                    raise ValueError("Malformed update package: Executable missing.")

                target_exe = next(
                    (f for f in exe_files if "transcriptor" in f.lower()),
                    exe_files[0]
                )

                zf.extract(target_exe, base_dir)
                extracted_full_path = os.path.join(base_dir, target_exe)

            # Cleanup download artifact and perform atomic rotation
            os.remove(dest_path)
            final_exe_path = dest_path[:-4] + ".exe"

            if os.path.exists(final_exe_path):
                try:
                    os.remove(final_exe_path)
                except OSError:
                    pass

            os.rename(extracted_full_path, final_exe_path)
            msg = "Binary extraction successful."
            logger.info(f"Update Task: Binary deployed to: {final_exe_path}")

        except Exception as e:
            logger.error(f"Update Task: Failed to unpack binary package: {e}")
            success = False
            msg = f"Extraction failure: {e}"

    on_complete((success, msg))


# -----------------------------------------------------------------------------
# TELEMETRY AND REPORTING WORKERS
# -----------------------------------------------------------------------------

def submit_feedback_task(
        payload: Dict[str, Any],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Dispatch user feedback to the remote collection endpoint.
    """
    success, msg = network.submit_feedback(payload)
    on_complete((success, msg))

def submit_error_report_task(
        payload: Dict[str, Any],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Dispatch diagnostic crash metadata to the remote collection endpoint.
    """
    success, msg = network.submit_error_report(payload)
    on_complete((success, msg))