from __future__ import annotations

"""
Session Management Controller.

Handles global state lifecycle operations, including factory resets of 
configuration and maintenance of the persistent cache repository.
Ensures UI synchronization following state mutations.
"""

import logging
import os
import tkinter.messagebox as mb
from typing import TYPE_CHECKING

from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.shared.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.coordinator import AppController

# Local logger for precise traceability
logger = logging.getLogger(__name__)


# ==============================================================================
# SESSION MANAGER CLASS
# ==============================================================================

class SessionManager:
    """
    Delegate responsible for destructive and maintenance-related session tasks.
    """

    def __init__(self, coordinator: AppController) -> None:
        """
        Initialize the delegate with a reference to the application hub.
        """
        self.main = coordinator

    def reset_config(self) -> None:
        """
        Restore all application settings to their factory domain defaults.

        Requires explicit user confirmation via a modal dialog. Mutates the
        active config dictionary in-place to preserve object references.
        """
        # 1. VALIDATION: Request user confirmation
        confirm = mb.askyesno(
            i18n.t("gui.dialogs.confirm_title"),
            "Reset all settings to defaults?"
        )

        if confirm:
            # 2. MUTATION: Update existing config object without replacing it
            # This ensures that all UI-bound references stay valid.
            self.main.config.clear()
            self.main.config.update(domain_cfg.get_default_config(os.getcwd()))

            # 3. SYNCHRONIZATION: Refresh the view to reflect new state
            self.main.synchronizer.sync_to_view()

            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings reset.")
            logger.info("SessionManager: Configuration successfully reset to defaults.")

    def purge_cache(self) -> None:
        """
        Atomically clear the local processing cache repository.

        Removes all entries from the SQLite cache database and reclaims space.
        Uses the injected cache port from the coordinator.
        """
        # 1. VALIDATION: Safety check before deletion
        if mb.askyesno("Purge Cache", "Clear the local processing cache?"):
            try:
                # 2. EXECUTION: Delegate to infrastructure layer
                self.main.get_cache().purge_all()

                mb.showinfo(
                    "Cache Cleared",
                    "Local cache has been successfully purged."
                )
                logger.info("SessionManager: Persistent cache purged by user.")

            except Exception as e:
                # 3. ERROR HANDLING: Capture IO or Database locks
                error_msg = f"Failed to purge cache:\n{e}"
                logger.error(f"SessionManager: {error_msg}")
                mb.showerror("Error", error_msg)