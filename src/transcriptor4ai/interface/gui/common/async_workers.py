from __future__ import annotations

"""
GUI Background Worker Tasks.

Orchestrates long-running operations in separate threads to maintain GUI 
responsiveness. These workers act as thin wrappers around Application 
Services, ensuring that thread lifecycle and UI callbacks are handled safely.
"""

import logging
import threading
from typing import Any, Callable, Dict, Optional, Tuple

# Application Layer
from transcriptor4ai.application.pipeline.orchestrator import run_pipeline
from transcriptor4ai.application.services.update_service import UpdateManager

# Domain Ports (for DI type hinting)
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.domain.ports.user_port import IUserContext

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PIPELINE WORKERS
# ==============================================================================

def run_pipeline_task(
        fs: IFileSystem,
        cache: ICacheRepository,
        user_context: IUserContext,
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        on_complete: Callable[[Any], None],
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """
    Execute the transcription pipeline in a background daemon thread.
    """
    try:
        if cancellation_event and cancellation_event.is_set():
            logger.info("Worker: Pipeline aborted before start.")
            return

        # 1. EXECUTE: Call the decoupled orchestrator with injected ports
        result = run_pipeline(
            fs=fs,
            cache=cache,
            user_context=user_context,
            config=config,
            overwrite=overwrite,
            dry_run=dry_run,
            cancellation_event=cancellation_event
        )

        # 2. CALLBACK: Marshal results back to the UI thread
        if not (cancellation_event and cancellation_event.is_set()):
            on_complete(result)

    except Exception as e:
        logger.critical(f"Worker: Pipeline critical failure: {e}", exc_info=True)
        on_complete(e)


# ==============================================================================
# UPDATE & NETWORK WORKERS
# ==============================================================================

def run_update_cycle_task(
        update_manager: UpdateManager,
        current_version: str,
        on_complete: Callable[[], None]
) -> None:
    """
    Execute the full OTA update lifecycle (Check -> Download -> Verify -> Unpack).

    Delegates all technical logic to the UpdateManager application service.
    """
    try:
        # 1. PROCESS: Run the silent background cycle
        update_manager.run_silent_cycle(current_version)

        # 2. NOTIFY: Signal the UI that the state has changed
        on_complete()
    except Exception as e:
        logger.error(f"Worker: Update cycle failed: {e}")
        on_complete()


def run_pricing_sync_task(
        pricing_service: Any,  # Implementation of Pricing synchronization
        on_complete: Callable[[Optional[Dict[str, Any]]], None]
) -> None:
    """
    Synchronize model data from the remote repository.
    """
    try:
        success = pricing_service.sync_remote_data()
        # In a real scenario, we might return the fetched data or just a signal
        on_complete(None)
    except Exception as e:
        logger.error(f"Worker: Pricing sync failed: {e}")
        on_complete(None)


# ==============================================================================
# TELEMETRY WORKERS
# ==============================================================================

def submit_telemetry_task(
        client: Any,  # Implementation of TelemetryApiClient
        payload: Dict[str, Any],
        is_error_report: bool,
        on_complete: Callable[[Tuple[bool, str]], None]
) -> None:
    """
    Dispatch feedback or crash reports to the remote endpoint.
    """
    try:
        if is_error_report:
            res = client.submit_error_report(payload)
        else:
            res = client.submit_feedback(payload)
        on_complete(res)
    except Exception as e:
        logger.error(f"Worker: Telemetry submission failed: {e}")
        on_complete((False, str(e)))