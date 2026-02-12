from __future__ import annotations

"""
User Feedback Hub Dialog.

Provides a professional modal interface for user feedback and bug reporting.
Orchestrates data validation and non-blocking submission to the telemetry
service using the standard async worker infrastructure.
"""

import logging
import platform
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, Tuple

import customtkinter as ctk

from transcriptor4ai.infrastructure.logging import get_recent_logs
from transcriptor4ai.infrastructure.network.telemetry_api_client import TelemetryApiClient
from transcriptor4ai.interface.gui.common import async_workers
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

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
        parent: Reference to the application main window for hierarchy and threading.
    """
    # 1. INITIALIZATION: Setup modal window properties
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Feedback Hub")
    toplevel.geometry("500x600")
    toplevel.resizable(False, False)
    toplevel.grab_set()

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================
    ctk.CTkLabel(
        toplevel,
        text="Send Feedback",
        font=("Roboto", 22, "bold")
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        toplevel,
        text="Help us improve Transcriptor4AI.",
        text_color="gray"
    ).pack(pady=(0, 20))

    # FORM CONTAINER
    content_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    content_frame.pack(fill="x", padx=30)

    # 1. CATEGORY: Report Type Selector
    ctk.CTkLabel(content_frame, text=i18n.t("gui.feedback.type_label"), anchor="w").pack(fill="x")
    report_types = ["Bug Report", "Feature Request", "General Feedback", "Other"]
    report_type = ctk.CTkComboBox(content_frame, values=report_types, state="readonly")
    report_type.set(report_types[0])
    report_type.pack(fill="x", pady=(0, 15))

    # 2. SUBJECT: User summary
    ctk.CTkLabel(content_frame, text="Subject:", anchor="w").pack(fill="x")
    subject = ctk.CTkEntry(content_frame, placeholder_text="e.g. Error in Token Counting")
    subject.pack(fill="x", pady=(0, 15))

    # 3. MESSAGE: Detailed feedback
    ctk.CTkLabel(content_frame, text="Message:", anchor="w").pack(fill="x")
    msg = ctk.CTkTextbox(content_frame, height=150)
    msg.pack(fill="x", pady=(0, 15))

    # 4. PRIVACY: Log inclusion control
    chk_logs = ctk.CTkCheckBox(
        content_frame,
        text="Include technical logs (Helps fixing bugs faster)",
        font=("Any", 12),
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
        """Handle network response on the main UI thread."""
        success, message = result
        btn_send.configure(state="normal")

        if success:
            logger.info("FeedbackModal: User feedback successfully transmitted.")
            mb.showinfo(
                i18n.t("gui.dialogs.success_title"),
                "Thank you! Your feedback has been sent."
            )
            toplevel.destroy()
        else:
            logger.error(f"FeedbackModal: Transmission failed -> {message}")
            status_lbl.configure(text=f"Error: {message}", text_color=COLOR_ERROR)
            mb.showerror(
                i18n.t("gui.dialogs.error_title"),
                f"Failed to send feedback:\n{message}"
            )

    def _validate_and_send() -> None:
        """Validate inputs and dispatch the generic telemetry worker."""
        # 1. VALIDATION: Ensure non-empty mandatory fields
        if not subject.get().strip() or not msg.get("1.0", "end").strip():
            mb.showwarning(
                i18n.t("gui.dialogs.error_title"),
                "Please fill in both Subject and Message."
            )
            return

        # 2. UI FEEDBACK: Disable triggers to prevent double submission
        btn_send.configure(state="disabled")
        status_lbl.configure(text="Transmitting feedback...", text_color=COLOR_PRIMARY)

        # 3. PAYLOAD CONSTRUCTION: Aggregate system and user data
        payload: Dict[str, Any] = {
            "type": report_type.get(),
            "subject": subject.get().strip(),
            "message": msg.get("1.0", "end").strip(),
            "version": const.CURRENT_CONFIG_VERSION,
            "os": f"{platform.system()} {platform.release()}",
            "logs": get_recent_logs(100) if chk_logs.get() else "User opted out of logs."
        }

        # 4. DISPATCH: Execute network task in background thread
        client = TelemetryApiClient()
        threading.Thread(
            target=async_workers.submit_telemetry_task,
            args=(
                client,
                payload,
                False,
                lambda res: parent.after(0, lambda: _on_submission_complete(res))
            ),
            daemon=True
        ).start()

    # ==========================================================================
    # ACTION FOOTER
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
        font=("Any", 12, "bold"),
        command=_validate_and_send
    )
    btn_send.pack(side="left", expand=True)