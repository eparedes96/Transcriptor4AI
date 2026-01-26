from __future__ import annotations

"""
Configuration Profile Controller.

Manages the lifecycle of named configuration presets (profiles). Coordinates 
the synchronization between the active UI state, transient session data, 
and the persistent application state using injected repository ports.
"""

import logging
import os
import tkinter.messagebox as mb
from typing import TYPE_CHECKING, List

import customtkinter as ctk

from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to prevent circular imports with the Main Controller
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PROFILE CONTROLLER
# ==============================================================================

class ProfileController:
    """
    Controller responsible for preset management: Load, Save, and Delete.
    """

    def __init__(self, main_controller: AppController) -> None:
        """
        Initialize the controller with a reference to the main app hub.
        """
        self.main = main_controller

    # ==========================================================================
    # PUBLIC PROFILE OPERATIONS
    # ==========================================================================

    def load_profile(self) -> None:
        """
        Apply a saved configuration preset to the active execution session.

        Retrieves the profile from state, merges it with current domain
        defaults to ensure schema safety, and triggers a full view refresh.
        """
        # 1. VALIDATION: Check if a valid profile is selected in the UI
        view = self.main.settings_view
        name = view.combo_profiles.get()

        if not name or name == i18n.t("gui.profiles.no_selection"):
            return

        # 2. RETRIEVAL: Access profile data from the global state
        profiles = self.main.app_state.get("saved_profiles", {})
        if name not in profiles:
            logger.warning(f"Profiles: Selected profile '{name}' not found in state.")
            return

        logger.info(f"Profiles: Loading preset '{name}' into active session.")

        # 3. MERGE: Layer profile data over fresh defaults for version compatibility
        # Current CWD is used as the base path for defaults
        merged_config = domain_cfg.get_default_config(os.getcwd())
        merged_config.update(profiles[name])

        # 4. SYNC: Update session state and refresh all UI components
        self.main.config.update(merged_config)
        self.main.sync_view_from_config()

        # Restore ComboBox state which might have been reset by sync
        view.combo_profiles.set(name)
        view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        mb.showinfo(
            i18n.t("gui.dialogs.success_title"),
            i18n.t("gui.profiles.saved", name=name)
        )

    def save_profile(self) -> None:
        """
        Persist the current UI state as a named configuration preset.
        """
        # 1. INPUT: Prompt user for a new profile name
        dialog = ctk.CTkInputDialog(
            text=i18n.t("gui.profiles.prompt_name"),
            title="Save Profile"
        )
        name = dialog.get_input()

        if not name:
            return

        name = name.strip()
        profiles = self.main.app_state.setdefault("saved_profiles", {})

        # 2. COLLISION: Handle existing profile overwrite confirmation
        if name in profiles:
            confirm = mb.askyesno(
                i18n.t("gui.profiles.confirm_overwrite_title"),
                i18n.t("gui.profiles.confirm_overwrite_msg", name=name)
            )
            if not confirm:
                return

        # 3. PERSIST: Sync UI to data and save via the Repository Port
        self.main.sync_config_from_view()

        # Deep copy to prevent transient changes affecting the saved state
        profiles[name] = self.main.config.copy()

        # Access repository through the main hub to maintain Hexagonal decoupling
        self.main.get_config_repo().save_app_state(self.main.app_state)

        # 4. REFRESH: Update UI lists and notify user
        self._update_profile_list(name)
        logger.info(f"Profiles: Preset '{name}' successfully persisted.")
        mb.showinfo(
            i18n.t("gui.dialogs.saved_title"),
            i18n.t("gui.profiles.saved", name=name)
        )

    def delete_profile(self) -> None:
        """
        Remove a configuration preset from persistent storage.
        """
        # 1. VALIDATION: Check selection
        view = self.main.settings_view
        name = view.combo_profiles.get()

        if not name or name == i18n.t("gui.profiles.no_selection"):
            return

        # 2. CONFIRMATION: Prevent accidental data loss
        profiles = self.main.app_state.get("saved_profiles", {})
        if name in profiles:
            confirm = mb.askyesno(
                i18n.t("gui.dialogs.confirm_title"),
                i18n.t("gui.profiles.confirm_delete", name=name)
            )

            # 3. EXECUTION: Remove and persist state change
            if confirm:
                del profiles[name]
                self.main.get_config_repo().save_app_state(self.main.app_state)
                self._update_profile_list()
                logger.info(f"Profiles: Preset '{name}' removed.")

    # ==========================================================================
    # PRIVATE UI HELPERS
    # ==========================================================================

    def _update_profile_list(self, select_name: str = "") -> None:
        """
        Synchronize the profile ComboBox with the current data in state.
        """
        view = self.main.settings_view
        names: List[str] = sorted(list(self.main.app_state.get("saved_profiles", {}).keys()))

        # Update widget values
        view.combo_profiles.configure(values=names)

        # Set active selection
        if select_name:
            view.combo_profiles.set(select_name)
        else:
            view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))