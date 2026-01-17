from __future__ import annotations

"""
Crash Reporting Modal.

Displays critical errors and allows sending logs to the developer.
"""

import logging
import platform
import threading
import tkinter.messagebox as mb
from typing import Optional, Tuple

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.infra.logging import get_recent_logs
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


def show_crash_modal(error_msg: str, stack_trace: str, parent: Optional[ctk.CTk] = None) -> None:
    """
    Display critical error details with reporting capability.
    """
    is_root_created = False
    if parent is None:
        parent = ctk.CTk()
        parent.withdraw()
        is_root_created = True

    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.crash.title"))
    toplevel.geometry("700x600")
    toplevel.grab_set()

    ctk.CTkLabel(
        toplevel,
        text=i18n.t("gui.crash.header"),
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#E04F5F"
    ).pack(pady=(20, 10))

    ctk.CTkLabel(toplevel, text="The application has encountered an unexpected problem.").pack()

    # Traceback Area
    textbox = ctk.CTkTextbox(toplevel, font=("Consolas", 10), height=200)
    textbox.insert("1.0", f"Error: {error_msg}\n\n{stack_trace}")
    textbox.configure(state="disabled")
    textbox.pack(fill="both", expand=True, padx=20, pady=10)

    # User Context
    ctk.CTkLabel(toplevel, text="What were you doing? (Optional):", anchor="w").pack(fill="x", padx=20)
    user_comment = ctk.CTkTextbox(toplevel, height=60)
    user_comment.pack(fill="x", padx=20, pady=(0, 10))

    status_lbl = ctk.CTkLabel(toplevel, text="", text_color="gray", font=("Any", 10))
    status_lbl.pack(pady=(0, 5))

    def _on_reported(result: Tuple[bool, str]) -> None:
        success, message = result
        btn_report.configure(state="normal")
        if success:
            status_lbl.configure(text="Report sent successfully. Thank you.", text_color="green")
            mb.showinfo("Report Sent", "Error report submitted. We will investigate this issue.")
            if is_root_created:
                parent.destroy()
            else:
                toplevel.destroy()
        else:
            status_lbl.configure(text="Failed to send report.", text_color="red")
            mb.showerror("Submission Error", f"Could not send report:\n{message}")

    def _send_report() -> None:
        btn_report.configure(state="disabled")
        status_lbl.configure(text="Sending report...", text_color="#3B8ED0")

        payload = {
            "error": error_msg,
            "stack_trace": stack_trace,
            "user_comment": user_comment.get("1.0", "end"),
            "app_version": const.CURRENT_CONFIG_VERSION,
            "os": platform.system(),
            "logs": get_recent_logs(150)
        }

        threading.Thread(
            target=threads.submit_error_report_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_reported(res))),
            daemon=True
        ).start()

    def _close() -> None:
        if is_root_created:
            parent.destroy()
        else:
            toplevel.destroy()

    # Buttons
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=20)

    ctk.CTkButton(
        btn_frame,
        text="Copy Error",
        command=lambda: parent.clipboard_append(f"Error: {error_msg}\n\n{stack_trace}")
    ).pack(side="left", padx=5)

    btn_report = ctk.CTkButton(
        btn_frame,
        text="Send Error Report",
        fg_color="#E04F5F",
        hover_color="#A03541",
        command=_send_report
    )
    btn_report.pack(side="left", padx=5, expand=True)

    ctk.CTkButton(
        btn_frame,
        text="Close",
        fg_color="#3B8ED0",
        hover_color="#36719F",
        command=_close
    ).pack(side="right", padx=5)

    if is_root_created:
        parent.mainloop()