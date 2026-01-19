from __future__ import annotations

"""
OTA Update Interface Controller.

Coordinates the background update lifecycle with the GUI. Manages 
the transition from update detection to user notification and 
modal triggering.
"""

import logging
import tkinter.messagebox as mb
from typing import Any, Dict

import customtkinter as ctk

from transcriptor4ai.core.services.updater import UpdateManager, UpdateStatus
from transcriptor4ai.domain import constants as const
from transcriptor4ai.interface.gui.dialogs.update_modal import show_update_prompt_modal

logger = logging.getLogger(__name__)


class UpdateController:
    """
    Handles asynchronous update events and UI synchronization for OTA cycles.
    """

    def __init__(self, app: ctk.CTk, sidebar: Any, update_manager: UpdateManager):
        """
        Initialize the update controller.

        Args:
            app: Root application instance.
            sidebar: The Sidebar view containing the update badge.
            update_manager: The core UpdateManager service.
        """
        self.app = app
        self.sidebar = sidebar
        self.manager = update_manager

    def run_silent_cycle(self, manual: bool = False) -> None:
        """
        Execute a non-interactive update check and binary acquisition.

        Designed to be run in a background thread.
        """
        try:
            # Check and download if necessary using core service
            self.manager.run_silent_cycle(const.CURRENT_CONFIG_VERSION)

            info = self.manager.update_info.copy()
            if self.manager.status == UpdateStatus.READY:
                info["pending_path"] = self.manager.pending_path

            # Marshal the result back to the main thread
            self.app.after(0, lambda: self._on_update_checked(info, manual))

        except Exception as e:
            logger.error(f"OTA Lifecycle: Background check failed: {e}")

    def _on_update_checked(self, result: Dict[str, Any], is_manual: bool) -> None:
        """
        Process the result of an update check and update the UI.

        Args:
            result: Metadata from the update manager.
            is_manual: Whether the check was triggered by the user.
        """
        if result.get("has_update"):
            version = result.get("latest_version", "?")
            bin_url = result.get("binary_url", "")
            pending_path = result.get("pending_path", "")
            changelog = result.get("changelog", "No changelog provided.")
            browser_url = result.get("download_url", "")

            # Activate the notification badge in the sidebar
            self.sidebar.update_badge.configure(
                text=f"Update v{version}",
                state="normal",
                command=lambda: show_update_prompt_modal(
                    self.app, version, changelog,
                    bin_url, pending_path, browser_url
                )
            )
            self.sidebar.update_badge.grid(row=5, column=0, padx=20, pady=10)

            # If manual, trigger the modal immediately
            if is_manual:
                show_update_prompt_modal(
                    self.app, version, changelog,
                    bin_url, pending_path, browser_url
                )

        elif is_manual:
            mb.showinfo(
                "Update Check",
                "Application is already up to date."
            )