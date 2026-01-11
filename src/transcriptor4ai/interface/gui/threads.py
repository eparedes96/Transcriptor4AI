from __future__ import annotations

from typing import Dict, Any

import PySimpleGUI as sg
from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra import network
from transcriptor4ai.interface.gui.handlers import logger


def _run_pipeline_thread(
        window: sg.Window,
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool
) -> None:
    """Execute the pipeline in a background thread and signal the window."""
    try:
        result = run_pipeline(config, overwrite=overwrite, dry_run=dry_run)
        window.write_event_value("-THREAD-DONE-", result)
    except Exception as e:
        logger.critical(f"Critical failure in pipeline thread: {e}", exc_info=True)
        window.write_event_value("-THREAD-DONE-", e)


def _check_updates_thread(window: sg.Window, is_manual: bool = False) -> None:
    """
    Check for updates in a background thread.

    Args:
        window: The GUI window instance.
        is_manual: Whether the check was triggered by user action.
    """
    res = network.check_for_updates(cfg.CURRENT_CONFIG_VERSION)
    window.write_event_value("-UPDATE-FINISHED-", (res, is_manual))


def _download_update_thread(window: sg.Window, binary_url: str, dest_path: str) -> None:
    """
    Download the new binary in a background thread with progress reporting.
    """
    def progress_cb(percent: float) -> None:
        window.write_event_value("-DOWNLOAD-PROGRESS-", percent)

    success, msg = network.download_binary_stream(binary_url, dest_path, progress_cb)
    window.write_event_value("-DOWNLOAD-DONE-", (success, msg))


def _submit_feedback_thread(window: sg.Window, payload: Dict[str, Any]) -> None:
    """Submit feedback in a background thread."""
    success, msg = network.submit_feedback(payload)
    window.write_event_value("-FEEDBACK-SUBMITTED-", (success, msg))


def _submit_error_report_thread(window: sg.Window, payload: Dict[str, Any]) -> None:
    """Submit a technical crash report in a background thread."""
    success, msg = network.submit_error_report(payload)
    window.write_event_value("-ERROR-REPORT-SUBMITTED-", (success, msg))
