from __future__ import annotations

"""
OTA Update Prompt Dialog.

Provides a professional modal interface to notify users of new releases. 
Displays the changelog in a scrollable area and offers routing between 
automated background updates or manual browser-based acquisition.
"""

import logging
import webbrowser
from typing import Final

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_ACCENT: Final[str] = "#1F6AA5"
COLOR_ACCENT_HOVER: Final[str] = "#1A5A8A"


# ==============================================================================
# PUBLIC DIALOG API
# ==============================================================================

def show_update_prompt_modal(
        parent: ctk.CTk,
        latest_version: str,
        changelog: str,
        binary_url: str,
        dest_path: str,
        browser_url: str = ""
) -> bool:
    """
    Prompt the user to accept a remote update using a themed modal.

    This function blocks the execution flow (wait_window) to return a
    deterministic choice to the calling controller.

    Args:
        parent: Main application window for modal anchoring.
        latest_version: New release version string.
        changelog: Markdown or text description of changes.
        binary_url: Direct download link for automated OTA.
        dest_path: Local staging destination.
        browser_url: Fallback URL for manual download.

    Returns:
        bool: True if automated update is requested, False otherwise.
    """
    # 1. SETUP: Initialize state capture variable
    # Using a list to allow mutation within the inner scope functions
    update_requested = [False]

    # 2. INITIALIZATION: Build top-level window
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.dialogs.update_title"))
    toplevel.geometry("550x500")
    toplevel.resizable(False, False)
    toplevel.attributes("-topmost", True)
    toplevel.grab_set()  # Force interaction with the update prompt

    # ==========================================================================
    # UI CONSTRUCTION
    # ==========================================================================

    # Header: Version Announcement
    ctk.CTkLabel(
        toplevel,
        text=f"Version v{latest_version} is available!",
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color=COLOR_ACCENT
    ).pack(pady=(25, 5))

    ctk.CTkLabel(
        toplevel,
        text="A new update has been detected. Review the changes below:",
        text_color="gray"
    ).pack(pady=(0, 15))

    # Changelog: Scrollable Text Area
    # Provides context on what's new to encourage updates
    change_box = ctk.CTkTextbox(toplevel, height=220, font=("Consolas", 11))
    change_box.insert("1.0", f"--- WHAT'S NEW ---\n\n{changelog}")
    change_box.configure(state="disabled")
    change_box.pack(fill="x", padx=30, pady=10)

    # ==========================================================================
    # INTERNAL EVENT LOGIC
    # ==========================================================================

    def _on_automated_update() -> None:
        """Signal the controller to start the background OTA thread."""
        if binary_url and dest_path:
            update_requested[0] = True
            toplevel.destroy()
        else:
            # Fallback if binary direct link is missing in metadata
            logger.warning("UpdateModal: Missing binary URL for auto-update. Redirecting to browser.")
            _on_manual_download()

    def _on_manual_download() -> None:
        """Redirect user to the external release page."""
        webbrowser.open(browser_url or binary_url)
        toplevel.destroy()

    def _on_cancel() -> None:
        """Close modal without taking action."""
        toplevel.destroy()

    # ==========================================================================
    # ACTION BAR
    # ==========================================================================
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(side="bottom", fill="x", padx=30, pady=25)

    # Action: Automated Upgrade (Primary)
    btn_auto = ctk.CTkButton(
        btn_frame,
        text="Update Now (Auto)",
        fg_color=COLOR_ACCENT,
        hover_color=COLOR_ACCENT_HOVER,
        font=ctk.CTkFont(weight="bold"),
        command=_on_automated_update
    )
    btn_auto.pack(side="left", expand=True, padx=(0, 5))

    # Action: Manual acquisition (Secondary)
    btn_manual = ctk.CTkButton(
        btn_frame,
        text="Manual Download",
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", "#DCE4EE"),
        command=_on_manual_download
    )
    btn_manual.pack(side="left", expand=True, padx=5)

    # Action: Defer
    ctk.CTkButton(
        btn_frame,
        text="Later",
        fg_color="gray30",
        hover_color="gray20",
        command=_on_cancel
    ).pack(side="left", expand=True, padx=(5, 0))

    # 3. BLOCKING: Wait for user interaction before returning result
    parent.wait_window(toplevel)

    return update_requested[0]