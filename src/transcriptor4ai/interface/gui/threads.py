from __future__ import annotations

"""
Background workers for the GUI.

This module handles long-running tasks (pipeline execution, networking)
to prevent the UI from freezing. It communicates results back to the
main window via generic callbacks (CustomTkinter compatible).
"""

import logging
import threading
from typing import Dict, Any, Callable, Optional, Tuple

from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.domain import constants as const
from transcriptor4ai.infra import network

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Pipeline Workers
# -----------------------------------------------------------------------------
def run_pipeline_task(
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        on_complete: Callable[[Any], None],
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """
    Execute the transcription pipeline in a background thread.

    Args:
        config: The configuration dictionary for the pipeline.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to simulate the process.
        on_complete: Callback function to receive the result (PipelineResult or Exception).
        cancellation_event: Optional event to signal cancellation request.
    """
    try:
        if cancellation_event and cancellation_event.is_set():
            logger.info("Pipeline task cancelled before start.")
            return

        result = run_pipeline(config, overwrite=overwrite, dry_run=dry_run)

        if cancellation_event and cancellation_event.is_set():
            logger.info("Pipeline task cancelled after execution (result discarded).")
            return

        on_complete(result)

    except Exception as e:
        logger.critical(f"Critical failure in pipeline thread: {e}", exc_info=True)
        on_complete(e)


# -----------------------------------------------------------------------------
# Network Workers
# -----------------------------------------------------------------------------
def check_updates_task(
        on_complete: Callable[[Any, bool], None],
        is_manual: bool = False
) -> None:
    """
    Check for application updates in a background thread.

    Args:
        on_complete: Callback accepting (ResultDict, IsManualBool).
        is_manual: Whether the check was triggered by user action.
    """
    try:
        res = network.check_for_updates(const.CURRENT_CONFIG_VERSION)
        on_complete(res, is_manual)
    except Exception as e:
        logger.error(f"Update check failed in thread: {e}")
        on_complete({"has_update": False, "error": str(e)}, is_manual)


def download_update_task(
        binary_url: str,
        dest_path: str,
        on_progress: Callable[[float], None],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Download the new binary in a background thread with progress reporting.

    Args:
        binary_url: URL of the file to download.
        dest_path: Local path to save the file.
        on_progress: Callback accepting a float (0-100) for progress.
        on_complete: Callback accepting (SuccessBool, MessageStr).
    """
    success, msg = network.download_binary_stream(binary_url, dest_path, on_progress)
    on_complete((success, msg))


def submit_feedback_task(
        payload: Dict[str, Any],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Submit user feedback in a background thread.

    Args:
        payload: The feedback data dictionary.
        on_complete: Callback accepting (SuccessBool, MessageStr).
    """
    success, msg = network.submit_feedback(payload)
    on_complete((success, msg))


def submit_error_report_task(
        payload: Dict[str, Any],
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Submit a technical crash report in a background thread.

    Args:
        payload: The error report data.
        on_complete: Callback accepting (SuccessBool, MessageStr).
    """
    success, msg = network.submit_error_report(payload)
    on_complete((success, msg))