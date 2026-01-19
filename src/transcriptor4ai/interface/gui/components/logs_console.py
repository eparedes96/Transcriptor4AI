from __future__ import annotations

"""
System Diagnostics Console.

Provides a read-only terminal-like interface within the GUI for monitoring 
real-time application logs. Supports programmatic updates via background 
queues and manual clipboard synchronization for troubleshooting.
"""

from typing import Any

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

# -----------------------------------------------------------------------------
# LOGS VIEW CLASS
# -----------------------------------------------------------------------------

class LogsFrame(ctk.CTkFrame):
    """
    Dedicated diagnostic console frame.

    Utilizes a monospaced text buffer to display system events and
    process traces, maintaining a history of the current session.
    """

    def __init__(self, master: Any, **kwargs: Any):
        """
        Initialize the diagnostic console view.

        Args:
            master: Parent UI container.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Monospaced text buffer for log visualization
        self.textbox = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 10))
        self.textbox.grid(row=0, column=0, sticky="nsew")

        # -----------------------------------------------------------------------------
        # COMPONENT ACTIONS
        # -----------------------------------------------------------------------------
        self.btn_copy = ctk.CTkButton(
            self,
            text=i18n.t("gui.logs.copy"),
            command=self._copy_logs
        )
        self.btn_copy.grid(row=1, column=0, pady=10, sticky="e")

    def append_log(self, msg: str) -> None:
        """
        Atomically append a new diagnostic message to the console.

        Handles state transitions to ensure the buffer remains read-only
        to the user while allowing programmatic write access.

        Args:
            msg: Formatted log message string.
        """
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _copy_logs(self) -> None:
        """
        Synchronize the entire console buffer to the system clipboard.
        """
        self.master.clipboard_clear()
        self.master.clipboard_append(self.textbox.get("1.0", "end"))