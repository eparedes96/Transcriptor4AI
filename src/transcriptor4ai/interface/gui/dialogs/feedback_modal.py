from __future__ import annotations

"""
User Feedback Hub Dialog.

Constructs an interactive modal for submitting feature requests, bug reports, 
or general feedback. Implements form validation and utilizes a non-blocking 
background thread for network transmission.
"""

import logging
import platform
import threading
import tkinter.messagebox as mb
from typing import Tuple, Optional

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.infra.logging import get_recent_logs
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# PUBLIC DIALOG API
# -----------------------------------------------------------------------------

def show_feedback_window(parent: ctk.CTk) -> None:
    """
    Construct and display the Feedback modal window.

    Args:
        parent: Reference to the application main window.
    """
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Feedback Hub")
    toplevel.geometry("500x550")
    toplevel.resizable(False, False)
    toplevel.grab_set()

    # Visual Branding Section
    ctk.CTkLabel(
        toplevel,
        text="Send Feedback",
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=(20, 5))

    ctk.CTkLabel(
        toplevel,
        text="Help us improve Transcriptor4AI.",
        text_color="gray"
    ).pack(pady=(0, 20))

    # -----------------------------------------------------------------------------
    # FORM LAYOUT
    # -----------------------------------------------------------------------------
    content_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    content_frame.pack(fill="x", padx=20)

    # Classification Selector
    ctk.CTkLabel(content_frame, text=i18n.t("gui.feedback.type_label"), anchor="w").pack(fill="x")
    report_types = ["Bug Report", "Feature Request", "Other"]
    report_type = ctk.CTkComboBox(content_frame, values=report_types, state="readonly")
    report_type.set(report_types[0])
    report_type.pack(fill="x", pady=(0, 10))

    # Subject Input
    ctk.CTkLabel(content_frame, text="Subject:", anchor="w").pack(fill="x")
    subject = ctk.CTkEntry(content_frame)
    subject.pack(fill="x", pady=(0, 10))

    # Detailed Content Area
    ctk.CTkLabel(content_frame, text="Message:", anchor="w").pack(fill="x")
    msg = ctk.CTkTextbox(content_frame, height=150)
    msg.pack(fill="x", pady=(0, 10))

    # Privacy/Diagnostic Control
    chk_logs = ctk.CTkCheckBox(content_frame, text="Include recent logs", onvalue=True, offvalue=False)
    chk_logs.select()
    chk_logs.pack(anchor="w", pady=(0, 20))

    status_lbl = ctk.CTkLabel(toplevel, text="", text_color="gray")
    status_lbl.pack(pady=(0, 5))

    # -----------------------------------------------------------------------------
    # SUBMISSION LOGIC
    # -----------------------------------------------------------------------------

    def _on_sent(result: Tuple[bool, str]) -> None:
        """Callback for network task completion."""
        success, message = result
        btn_send.configure(state="normal")

        if success:
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Thank you! Your feedback has been sent.")
            toplevel.destroy()
        else:
            status_lbl.configure(text=f"Error: {message}", text_color="#E04F5F")
            mb.showerror(i18n.t("gui.dialogs.error_title"), f"Failed to send feedback:\n{message}")

    def _send() -> None:
        """Validate input and dispatch the feedback task to a daemon thread."""
        if not subject.get().strip() or not msg.get("1.0", "end").strip():
            mb.showerror(i18n.t("gui.dialogs.error_title"), "Please fill in Subject and Message.")
            return

        btn_send.configure(state="disabled")
        status_lbl.configure(text="Sending feedback...", text_color="#3B8ED0")

        payload = {
            "type": report_type.get(),
            "subject": subject.get(),
            "message": msg.get("1.0", "end"),
            "version": const.CURRENT_CONFIG_VERSION,
            "os": platform.system(),
            "logs": get_recent_logs(100) if chk_logs.get() else ""
        }

        # Asynchronous submission
        threading.Thread(
            target=threads.submit_feedback_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_sent(res))),
            daemon=True
        ).start()

    # -----------------------------------------------------------------------------
    # FOOTER ACTIONS
    # -----------------------------------------------------------------------------
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=10)

    btn_cancel = ctk.CTkButton(
        btn_frame,
        text="Cancel",
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", "#DCE4EE"),
        command=toplevel.destroy
    )
    btn_cancel.pack(side="left", expand=True, padx=5)

    btn_send = ctk.CTkButton(
        btn_frame,
        text="Send Feedback",
        fg_color="#3B8ED0",
        command=_send
    )
    btn_send.pack(side="left", expand=True, padx=5)