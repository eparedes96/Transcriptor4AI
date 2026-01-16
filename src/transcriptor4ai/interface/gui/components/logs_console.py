from __future__ import annotations

from typing import Any

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n


class LogsFrame(ctk.CTkFrame):
    """
    Read-only console to display system logs in the UI.
    """

    def __init__(self, master: Any, **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 10))
        self.textbox.grid(row=0, column=0, sticky="nsew")

        self.btn_copy = ctk.CTkButton(
            self,
            text=i18n.t("gui.logs.copy"),
            command=self._copy_logs
        )
        self.btn_copy.grid(row=1, column=0, pady=10, sticky="e")

    def append_log(self, msg: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _copy_logs(self) -> None:
        self.master.clipboard_clear()
        self.master.clipboard_append(self.textbox.get("1.0", "end"))
