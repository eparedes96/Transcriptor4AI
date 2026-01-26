from __future__ import annotations

"""
User Feedback Hub Dialog.

Constructs an interactive modal for submitting feature requests, bug reports, 
or general feedback. Implements form validation and utilizes a non-blocking 
background thread for network transmission via the Telemetry client.
"""

import logging
import platform
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, Tuple

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
COLOR_PRIMARY = "#1F6AA5"
COLOR_PRIMARY_HOVER = "#1A5A8A"
COLOR_ERROR = "#E04F5F"


# ==============================================================================
# PUBLIC DIALOG API
# ==============================================================================

def show_feedback_window(parent: ctk.CTk) -> None:
    """
    Construct and display the Feedback modal window.

    Args:
        parent: Reference to the application main window for hierarchy.
    """
    # 1. INITIALIZATION: Setup modal window properties
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Feedback Hub")
    toplevel.geometry("500x600")
    toplevel.resizable(False, False)
    toplevel.grab_set()  # Maintain modal focus

    # ==========================================================================
    # UI CONSTRUCTION: HEADER
    # ==========================================================================
    ctk.CTkLabel(
        toplevel,
        text="Send Feedback",
        font=ctk.CTkFont(size=22, weight="bold")
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        toplevel,
        text="Help us improve Transcriptor4AI.",
        text_color="gray"
    ).pack(pady=(0, 20))

    # ==========================================================================
    # UI CONSTRUCTION: FORM FIELDS
    # ==========================================================================
    content_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    content_frame.pack(fill="x", padx=30)

    # 1. CATEGORY: Report Type Selector
    ctk.CTkLabel(content_frame, text=i18n.t("gui.feedback.type_label"), anchor="w").pack(fill="x")
    report_types = ["Bug Report", "Feature Request", "General Feedback", "Other"]
    report_type = ctk.CTkComboBox(content_frame, values=report_types, state="readonly")
    report_type.set(report_types[0])
    report_type.pack(fill="x", pady=(0, 15))

    # 2. SUBJECT: Brief identification
    ctk.CTkLabel(content_frame, text="Subject:", anchor="w").pack(fill="x")
    subject = ctk.CTkEntry(content_frame, placeholder_text="e.g. Error in Token Counting")
    subject.pack(fill="x", pady=(0, 15))

    # 3. MESSAGE: Qualitative details
    ctk.CTkLabel(content_frame, text="Message:", anchor="w").pack(fill="x")
    msg = ctk.CTkTextbox(content_frame, height=150)
    msg.pack(fill="x", pady=(0, 15))

    # 4. PRIVACY: Control over diagnostic logs
    chk_logs = ctk.CTkCheckBox(
        content_frame,
        text="Include technical logs (Helps fixing bugs faster)",
        font=ctk.CTkFont(size=12),
        onvalue=True,
        offvalue=False
    )
    chk_logs.select()
    chk_logs.pack(anchor="w", pady=(5, 10))

    status_lbl = ctk.CTkLabel(toplevel, text="", font=("Any", 11))
    status_lbl.pack(pady=(10, 0))

    # ==========================================================================
    # INTERNAL LOGIC & CALLBACKS
    # ==========================================================================

    def _on_submission_complete(result: Tuple[bool, str]) -> None:
        """Process the network response on the main UI thread."""
        success, message = result
        btn_send.configure(state="normal")

        if success:
            logger.info("FeedbackModal: User feedback successfully transmitted.")
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Thank you! Your feedback has been sent.")
            toplevel.destroy()
        else:
            logger.error(f"FeedbackModal: Transmission failed -> {message}")
            status_lbl.configure(text=f"Error: {message}", text_color=COLOR_ERROR)
            mb.showerror(i18n.t("gui.dialogs.error_title"), f"Failed to send feedback:\n{message}")

    def _validate_and_send() -> None:
        """Verify inputs and initiate the background telemetry task."""
        # 1. VALIDATION: Check for mandatory content
        if not subject.get().strip() or not msg.get("1.0", "end").strip():
            mb.showwarning(i18n.t("gui.dialogs.error_title"), "Please fill in both Subject and Message.")
            return

        # 2. UI STATE: Provide immediate feedback
        btn_send.configure(state="disabled")
        status_lbl.configure(text="Transmitting feedback...", text_color=COLOR_PRIMARY)

        # 3. PAYLOAD: Assemble telemetry data
        payload: Dict[str, Any] = {
            "type": report_type.get(),
            "subject": subject.get().strip(),
            "message": msg.get("1.0", "end").strip(),
            "version": const.CURRENT_CONFIG_VERSION,
            "os": f"{platform.system()} {platform.release()}",
            "logs": get_recent_logs(100) if chk_logs.get() else "User opted out of logs."
        }

        # 4. DISPATCH: Run network task in a daemon thread to avoid blocking
        threading.Thread(
            target=async_workers.submit_feedback_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_submission_complete(res))),
            daemon=True
        ).start()

    # ==========================================================================
    # ACTION BAR
    # ==========================================================================
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=30, pady=20)

    btn_cancel = ctk.CTkButton(
        btn_frame,
        text="Cancel",
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", "#DCE4EE"),
        command=toplevel.destroy
    )
    btn_cancel.pack(side="left", expand=True, padx=(0, 10))

    btn_send = ctk.CTkButton(
        btn_frame,
        text="Send Feedback",
        fg_color=COLOR_PRIMARY,
        hover_color=COLOR_PRIMARY_HOVER,
        font=ctk.CTkFont(weight="bold"),
        command=_validate_and_send
    )
    btn_send.pack(side="left", expand=True)