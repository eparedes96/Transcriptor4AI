from __future__ import annotations

"""
OTA Update Prompt Dialog.

Constructs a standard confirmation modal when a new application version 
is detected. Acts as the gateway to the Over-The-Air (OTA) binary swap 
lifecycle, allowing users to choose between automatic background acquisition 
or manual download via a web browser.
"""

import webbrowser
from tkinter import messagebox as mb

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

# -----------------------------------------------------------------------------
# PUBLIC DIALOG API
# -----------------------------------------------------------------------------

def show_update_prompt_modal(
        parent: ctk.CTk,
        latest_version: str,
        changelog: str,
        binary_url: str,
        dest_path: str,
        browser_url: str = ""
) -> bool:
    """
    Prompt the user to accept a remote update.

    If accepted and parameters for background downloading are present,
    returns a flag to initiate the update thread. Otherwise, provides
    web redirection as a fallback.

    Args:
        parent: Parent UI window reference.
        latest_version: Semantic version string of the new release.
        changelog: Description of changes in the latest version.
        binary_url: Direct download link for the binary asset.
        dest_path: Target local path for binary staging.
        browser_url: URL to the release page for manual acquisition.

    Returns:
        bool: True if the user chooses automatic background update, False otherwise.
    """
    # Use system-standard prompt for high-confidence updates
    message = f"Version v{latest_version} is available.\n\nDownload and install now?"

    if not mb.askyesno(
            i18n.t("gui.dialogs.update_title"),
            message
    ):
        return False

    # Check for background download capability
    if binary_url and dest_path:
        return True

    # Fallback to browser if parameters are missing
    webbrowser.open(browser_url)
    return False