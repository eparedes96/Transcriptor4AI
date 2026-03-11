from __future__ import annotations

"""
GUI Startup and Environment Orchestrator.

Handles the technical bootstrapping of the graphical interface, including 
diagnostic logging configuration, message queueing for cross-thread log 
rendering, and visual theme initialization.
"""

import logging
import queue
from logging.handlers import QueueHandler
from typing import TYPE_CHECKING

import customtkinter as ctk

from transcriptor4ai.infrastructure.logging import (
    LoggingConfig,
    configure_logging,
    get_default_gui_log_path,
)

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.logs_console import LogsFrame

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# DIAGNOSTIC BOOTSTRAP
# ==============================================================================

def init_diagnostic_system() -> queue.Queue[logging.LogRecord]:
    """
    Configure the global logging infrastructure and initialize the GUI queue.

    Returns:
        queue.Queue: The shared queue where LogRecords will be captured.
    """
    # 1. PHYSICAL LOGGING: Set up rotation file and console output
    log_path: str = get_default_gui_log_path()

    configure_logging(
        LoggingConfig(level="INFO", console=True, log_file=log_path)
    )

    logger.info("Startup: Diagnostic infrastructure online.")

    # 2. GUI INTERCEPTOR: Attach a QueueHandler to the root logger
    # This allows background tasks to send logs to the UI safely.
    gui_log_queue: queue.Queue[logging.LogRecord] = queue.Queue()
    gui_log_handler = QueueHandler(gui_log_queue)
    gui_log_handler.setLevel(logging.INFO)

    logging.getLogger().addHandler(gui_log_handler)

    return gui_log_queue


def setup_visual_theme() -> None:
    """
    Apply global CustomTkinter appearance settings.
    """
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    logger.debug("Startup: Visual theme applied (System Default).")


# ==============================================================================
# LOG RENDERING ENGINE
# ==============================================================================

def start_log_polling(
        app: ctk.CTk,
        log_queue: queue.Queue[logging.LogRecord],
        logs_view: LogsFrame
) -> None:
    """
    Initialize the recursive loop to flush logs from the queue into the UI.

    Args:
        app: The root application instance for scheduling.
        log_queue: The source queue containing captured logs.
        logs_view: The GUI component where logs are rendered.
    """
    # Standard format for the console display
    log_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        "%H:%M:%S"
    )

    def poll() -> None:
        """Internal recursive task scheduled on the UI mainloop."""
        try:
            # Process all pending messages in the queue
            while not log_queue.empty():
                record = log_queue.get_nowait()
                msg = log_formatter.format(record)

                # Critical check: Ensure the view is alive before writing
                if logs_view and hasattr(logs_view, "append_log"):
                    logs_view.append_log(msg)

        except queue.Empty:
            pass
        except Exception as e:
            # Avoid crashing the UI thread if log formatting fails
            logger.error(f"Startup: Log polling interruption: {e}")
        finally:
            # Re-schedule polling every 100ms
            app.after(100, poll)

    # Trigger the first execution
    app.after(100, poll)