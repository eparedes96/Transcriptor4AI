from __future__ import annotations

"""
OTA Update Interface Controller.

Coordinates the background update lifecycle with the graphical interface. 
Manages the transition from release detection (via UpdateManager) to user 
notification, ensuring thread-safe UI updates and modal triggering.
"""

import logging
import tkinter.messagebox as mb
from typing import Any, Dict

import customtkinter as ctk

from transcriptor4ai.application.services.update_service import UpdateManager, UpdateStatus
from transcriptor4ai.interface.gui.dialogs.update_modal import show_update_prompt_modal
from transcriptor4ai.shared import constants as const

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# UPDATE CONTROLLER
# ==============================================================================

class UpdateController:
    """
    Controller responsible for synchronizing background update states with the UI.
    """

    def __init__(self, app: ctk.CTk, sidebar: Any, update_manager: UpdateManager) -> None:
        """
        Initialize the update controller.

        Args:
            app: Root application instance (for thread marshalling).
            sidebar: The Sidebar view instance containing the update badge.
            update_manager: Injected application service for OTA logic.
        """
        self.app = app
        self.sidebar = sidebar
        self.manager = update_manager

    # ==========================================================================
    # LIFECYCLE MANAGEMENT
    # ==========================================================================

    def run_silent_cycle(self, manual: bool = False) -> None:
        """
        Execute a non-interactive update check and staging process.

        Note: This method is designed to be executed within a background thread.
        """
        try:
            # 1. PROCESS: Invoke the application service to check remote versions
            # This involves network I/O and cryptographic verification
            self.manager.run_silent_cycle(const.CURRENT_CONFIG_VERSION)

            # 2. STATE: Capture metadata snapshot for UI synchronization
            info = self.manager.update_info.copy()
            if self.manager.status == UpdateStatus.READY:
                # Attach the verified local path if the download finished
                info["pending_path"] = self.manager.pending_path

            # 3. MARSHAL: Schedule UI update on the main thread
            self.app.after(0, lambda: self._on_update_checked(info, manual))

        except Exception as e:
            logger.error(f"UpdateController: Background check failed: {e}", exc_info=True)

    # ==========================================================================
    # UI SYNCHRONIZATION
    # ==========================================================================

    def _on_update_checked(self, result: Dict[str, Any], is_manual: bool) -> None:
        """
        Update the interface based on the results of the update check.

        Args:
            result: Metadata dictionary from the UpdateManager.
            is_manual: Flag indicating if the check was user-initiated.
        """
        # 1. VALIDATION: Check if a newer version exists
        if result.get("has_update"):
            version = result.get("latest_version", "?")
            bin_url = result.get("binary_url", "")
            pending_path = result.get("pending_path", "")
            changelog = result.get("changelog", "No changelog provided.")
            browser_url = result.get("download_url", "")

            logger.info(f"UpdateController: New release detected -> v{version}")

            # 2. VIEW UPDATE: Configure and display the notification badge
            # We assume the sidebar has an 'update_badge' button pre-defined
            self.sidebar.update_badge.configure(
                text=f"Update v{version}",
                state="normal",
                command=lambda: show_update_prompt_modal(
                    self.app, version, changelog,
                    bin_url, pending_path, browser_url
                )
            )
            self.sidebar.update_badge.grid(row=5, column=0, padx=20, pady=10)

            # 3. INTERACTION: Trigger modal immediately if manual check
            if is_manual:
                show_update_prompt_modal(
                    self.app, version, changelog,
                    bin_url, pending_path, browser_url
                )

        # 4. FALLBACK: Inform user if manual check found no updates
        elif is_manual:
            mb.showinfo(
                "Update Check",
                "Application is already up to date."
            )