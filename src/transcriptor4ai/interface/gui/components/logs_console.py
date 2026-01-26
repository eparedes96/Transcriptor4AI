from __future__ import annotations

"""
System Diagnostics Console Component.

Provides a read-only terminal-like interface within the GUI for monitoring 
real-time application logs. Supports programmatic updates via background 
queues and manual clipboard synchronization for troubleshooting.
"""

import logging
from typing import Any, Final

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
MONOSPACE_FONT: Final[tuple[str, int]] = ("Consolas", 10)


# ==============================================================================
# VIEW COMPONENT: LOGS FRAME
# ==============================================================================

class LogsFrame(ctk.CTkFrame):
    """
    Dedicated diagnostic console frame.

    Utilizes a monospaced text buffer to display system events and
    process traces, maintaining a history of the current session.
    """

    def __init__(self, master: Any, **kwargs: Any) -> None:
        """
        Initialize the diagnostic console view.

        Args:
            master: Parent UI container.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        # 1. LAYOUT: Configure grid for expansion
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. COMPONENT: Log Buffer (Read-Only)
        self.textbox = ctk.CTkTextbox(
            self,
            state="disabled",
            font=MONOSPACE_FONT,
            wrap="none"  # Prevent wrapping for better trace readability
        )
        self.textbox.grid(row=0, column=0, sticky="nsew")

        # 3. ACTION: Clipboard Synchronization
        self.btn_copy = ctk.CTkButton(
            self,
            text=i18n.t("gui.logs.copy"),
            command=self._copy_logs,
            width=100
        )
        self.btn_copy.grid(row=1, column=0, pady=10, sticky="e")

        logger.debug("UI: LogsConsole initialized.")

    # ==========================================================================
    # PUBLIC API
    # ==========================================================================

    def append_log(self, msg: str) -> None:
        """
        Atomically append a new diagnostic message to the console.

        Handles state transitions to ensure the buffer remains read-only
        to the user while allowing programmatic write access.

        Args:
            msg: Formatted log message string.
        """
        # 1. UNLOCK: Enable writing
        self.textbox.configure(state="normal")

        # 2. WRITE: Append message with newline
        self.textbox.insert("end", msg + "\n")

        # 3. SCROLL: Auto-follow latest logs
        self.textbox.see("end")

        # 4. LOCK: Restore read-only state
        self.textbox.configure(state="disabled")

    # ==========================================================================
    # INTERNAL EVENT HANDLERS
    # ==========================================================================

    def _copy_logs(self) -> None:
        """
        Synchronize the entire console buffer to the system clipboard.
        """
        try:
            content = self.textbox.get("1.0", "end")
            self.master.clipboard_clear()
            self.master.clipboard_append(content)
            logger.debug("UI: Logs copied to clipboard.")
        except Exception as e:
            logger.error(f"UI: Failed to copy logs: {e}")