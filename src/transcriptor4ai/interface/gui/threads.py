from __future__ import annotations

"""
Background workers for the GUI.

This module handles long-running tasks (pipeline execution, networking)
to prevent the UI from freezing. It communicates results back to the
main window via PySimpleGUI events.
"""

import logging
from typing import Dict, Any, Callable

import PySimpleGUI as sg

from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra import network

# Initialize module-level logger to avoid circular dependency with handlers
logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Pipeline Workers
# -----------------------------------------------------------------------------
def run_pipeline_task(
        window: sg.Window,
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool
) -> None:
    """
    Execute the transcription pipeline in a background thread.

    Args:
        window: The GUI window instance to receive events.
        config: The configuration dictionary for the pipeline.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to simulate the process.
    """
    try:
        result = run_pipeline(config, overwrite=overwrite, dry_run=dry_run)
        window.write_event_value("-THREAD-DONE-", result)
    except Exception as e:
        logger.critical(f"Critical failure in pipeline thread: {e}", exc_info=True)
        window.write_event_value("-THREAD-DONE-", e)


# -----------------------------------------------------------------------------
# Network Workers
# -----------------------------------------------------------------------------
def check_updates_task(window: sg.Window, is_manual: bool = False) -> None:
    """
    Check for application updates in a background thread.

    Args:
        window: The GUI window instance.
        is_manual: Whether the check was triggered by user action.
    """
    try:
        res = network.check_for_updates(cfg.CURRENT_CONFIG_VERSION)
        window.write_event_value("-UPDATE-FINISHED-", (res, is_manual))
    except Exception as e:
        logger.error(f"Update check failed in thread: {e}")
        window.write_event_value("-UPDATE-FINISHED-", ({"has_update": False, "error": str(e)}, is_manual))


def download_update_task(window: sg.Window, binary_url: str, dest_path: str) -> None:
    """
    Download the new binary in a background thread with progress reporting.

    Args:
        window: The GUI window instance.
        binary_url: URL of the file to download.
        dest_path: Local path to save the file.
    """
    def progress_cb(percent: float) -> None:
        window.write_event_value("-DOWNLOAD-PROGRESS-", percent)

    success, msg = network.download_binary_stream(binary_url, dest_path, progress_cb)
    window.write_event_value("-DOWNLOAD-DONE-", (success, msg))


def submit_feedback_task(window: sg.Window, payload: Dict[str, Any]) -> None:
    """
    Submit user feedback in a background thread.

    Args:
        window: The GUI window instance.
        payload: The feedback data dictionary.
    """
    success, msg = network.submit_feedback(payload)
    window.write_event_value("-FEEDBACK-SUBMITTED-", (success, msg))


def submit_error_report_task(window: sg.Window, payload: Dict[str, Any]) -> None:
    """
    Submit a technical crash report in a background thread.

    Args:
        window: The GUI window instance.
        payload: The error report data.
    """
    success, msg = network.submit_error_report(payload)
    window.write_event_value("-ERROR-REPORT-SUBMITTED-", (success, msg))