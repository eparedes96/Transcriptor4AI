from __future__ import annotations

import webbrowser
from tkinter import messagebox as mb

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n


def show_update_prompt_modal(
        parent: ctk.CTk,
        latest_version: str,
        changelog: str,
        binary_url: str,
        dest_path: str,
        browser_url: str = ""
) -> bool:
    """
    Shows a modal for updates. Returns True if user accepts OTA download.
    """
    if not mb.askyesno(
            i18n.t("gui.dialogs.update_title"),
            f"Version v{latest_version} is available.\n\nDownload now?"
    ):
        return False

    if binary_url and dest_path:
        return True
    else:
        webbrowser.open(browser_url)
        return False
