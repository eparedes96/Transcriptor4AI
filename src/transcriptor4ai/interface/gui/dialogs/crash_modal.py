from __future__ import annotations

"""
Critical Crash Reporting Dialog.

Constructs a high-priority modal window to intercept and display unhandled 
exceptions. Provides diagnostic information including stack traces and local 
logs, allowing the user to submit detailed bug reports via an asynchronous 
background task.
"""

import logging
import platform
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, Optional, Tuple

import customtkinter as ctk

from transcriptor4ai.infrastructure.logging import get_recent_logs
from transcriptor4ai.interface.gui.common import async_workers
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_DANGER = "#E04F5F"
COLOR_DANGER_HOVER = "#A03541"
COLOR_ACCENT = "#1F6AA5"
COLOR_ACCENT_HOVER = "#1A5A8A"


# ==============================================================================
# PUBLIC DIALOG API
# ==============================================================================

def show_crash_modal(error_msg: str, stack_trace: str, parent: Optional[ctk.CTk] = None) -> None:
    """
    Instantiate and display the crash reporting interface.

    Handles the UI lifecycle and orchestrates background telemetry submission.

    Args:
        error_msg: The primary exception message.
        stack_trace: Full Python traceback string.
        parent: Optional reference to the main application window.
    """
    # 1. INITIALIZATION: Setup window context
    is_root_created = False
    if parent is None:
        parent = ctk.CTk()
        parent.withdraw()
        is_root_created = True

    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.crash.title"))
    toplevel.geometry("700x650")
    toplevel.grab_set()  # Force user attention by blocking parent interaction

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================

    # 2. HEADER: Branding and urgent notice
    ctk.CTkLabel(
        toplevel,
        text=i18n.t("gui.crash.header"),
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color=COLOR_DANGER
    ).pack(pady=(20, 10))

    ctk.CTkLabel(
        toplevel,
        text="A critical error occurred. Technical details have been captured.",
        font=ctk.CTkFont(size=13)
    ).pack(pady=(0, 10))

    # 3. DIAGNOSTICS: Read-only traceback display
    textbox = ctk.CTkTextbox(toplevel, font=("Consolas", 11), height=250)
    textbox.insert("1.0", f"CRITICAL ERROR: {error_msg}\n\n{stack_trace}")
    textbox.configure(state="disabled")
    textbox.pack(fill="both", expand=True, padx=20, pady=10)

    # 4. INPUT: Optional qualitative user context
    ctk.CTkLabel(
        toplevel,
        text="What were you doing when this happened? (Optional):",
        font=ctk.CTkFont(weight="bold"),
        anchor="w"
    ).pack(fill="x", padx=20, pady=(10, 5))

    user_comment = ctk.CTkTextbox(toplevel, height=80)
    user_comment.pack(fill="x", padx=20, pady=(0, 10))

    status_lbl = ctk.CTkLabel(toplevel, text="", font=("Any", 11), text_color="gray")
    status_lbl.pack(pady=(5, 5))

    # ==========================================================================
    # INTERNAL LOGIC & CALLBACKS
    # ==========================================================================

    def _on_report_complete(result: Tuple[bool, str]) -> None:
        """Handle telemetry task finalization on the main thread."""
        success, message = result
        btn_report.configure(state="normal")

        if success:
            logger.info("CrashModal: Report successfully transmitted.")
            mb.showinfo("Report Sent", "Diagnostic data submitted. Thank you for your help.")
            if is_root_created:
                parent.destroy()
            else:
                toplevel.destroy()
        else:
            logger.error(f"CrashModal: Transmission failed -> {message}")
            status_lbl.configure(text="Failed to send report.", text_color=COLOR_DANGER)
            mb.showerror("Submission Error", f"Could not send report:\n{message}")

    def _send_report() -> None:
        """Assemble diagnostic payload and dispatch to background thread."""
        btn_report.configure(state="disabled")
        status_lbl.configure(text="Transmitting diagnostics...", text_color=COLOR_ACCENT)

        # Build telemetry payload
        payload: Dict[str, Any] = {
            "error": error_msg,
            "stack_trace": stack_trace,
            "user_comment": user_comment.get("1.0", "end").strip(),
            "app_version": const.CURRENT_CONFIG_VERSION,
            "os_info": f"{platform.system()} {platform.release()}",
            "recent_logs": get_recent_logs(150)
        }

        # Threaded execution to maintain UI responsiveness
        threading.Thread(
            target=async_workers.submit_error_report_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_report_complete(res))),
            daemon=True
        ).start()

    def _close_app() -> None:
        """Terminate the process after crash notification."""
        if is_root_created:
            parent.destroy()
        else:
            toplevel.destroy()
        # Clean exit is handled by main.py exception hook but we ensure it here
        import sys
        sys.exit(1)

    # ==========================================================================
    # ACTION BAR
    # ==========================================================================
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=20)

    # Utility: Allow user to copy info for manual report/debugging
    ctk.CTkButton(
        btn_frame,
        text="Copy to Clipboard",
        command=lambda: parent.clipboard_append(f"Error: {error_msg}\n\n{stack_trace}")
    ).pack(side="left", padx=5)

    # Action: Automated Telemetry
    btn_report = ctk.CTkButton(
        btn_frame,
        text="Submit Bug Report",
        fg_color=COLOR_DANGER,
        hover_color=COLOR_DANGER_HOVER,
        font=ctk.CTkFont(weight="bold"),
        command=_send_report
    )
    btn_report.pack(side="left", padx=5, expand=True)

    # Action: Exit
    ctk.CTkButton(
        btn_frame,
        text="Close Application",
        fg_color="gray30",
        hover_color="gray20",
        command=_close_app
    ).pack(side="right", padx=5)

    if is_root_created:
        parent.mainloop()