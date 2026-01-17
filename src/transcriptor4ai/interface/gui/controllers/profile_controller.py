from __future__ import annotations

"""
Configuration Profile Management Controller.

Handles the full lifecycle of named configuration presets. Manages 
synchronization between the active UI state, the transient session config, 
and the persistent application state stored in the filesystem.
"""

import logging
import tkinter.messagebox as mb
from typing import TYPE_CHECKING

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# PROFILE LIFECYCLE MANAGER
# -----------------------------------------------------------------------------

class ProfileController:
    """
    Controller responsible for preset management (Save/Load/Delete).
    """

    def __init__(self, main_controller: AppController):
        """
        Initialize the controller with a reference to the main app orchestrator.

        Args:
            main_controller: Reference to the parent AppController instance.
        """
        self.controller = main_controller

    # -----------------------------------------------------------------------------
    # CORE OPERATIONS
    # -----------------------------------------------------------------------------

    def load_profile(self) -> None:
        """
        Apply a saved configuration preset to the active session.

        Retrieves the profile from the app state, merges it with current
        domain defaults to ensure schema compatibility with newer versions,
        and triggers a full UI synchronization.
        """
        view = self.controller.settings_view
        name = view.combo_profiles.get()

        if name == i18n.t("gui.profiles.no_selection"):
            return

        profiles = self.controller.app_state.get("saved_profiles", {})
        if name in profiles:
            logger.info(f"Session: Loading profile preset '{name}'.")

            # 1. Start with domain defaults for schema safety
            temp = cfg.get_default_config()
            # 2. Layer profile data on top
            temp.update(profiles[name])

            # 3. Synchronize transient config and refresh the entire View
            self.controller.config.update(temp)
            self.controller.sync_view_from_config()

            # 4. Restore UI selection state (as sync might reset widgets)
            view.combo_profiles.set(name)
            view.combo_stack.set(i18n.t("gui.combos.select_stack"))

            mb.showinfo(i18n.t("gui.dialogs.success_title"), f"Profile '{name}' loaded.")

    def save_profile(self) -> None:
        """
        Persist the current UI state as a named configuration preset.

        Prompts the user for a profile name, handles overwrite confirmations,
        and updates the persistent application state file.
        """
        dialog = ctk.CTkInputDialog(
            text=i18n.t("gui.profiles.prompt_name"),
            title="Save Profile"
        )
        name = dialog.get_input()

        if name:
            name = name.strip()
            profiles = self.controller.app_state.setdefault("saved_profiles", {})

            # Collision check
            if name in profiles:
                confirm = mb.askyesno(
                    i18n.t("gui.profiles.confirm_overwrite_title"),
                    i18n.t("gui.profiles.confirm_overwrite_msg", name=name)
                )
                if not confirm:
                    return

            # Scrape current values from all UI components into transient config
            self.controller.sync_config_from_view()

            # Persist a snapshot of the config dictionary
            profiles[name] = self.controller.config.copy()
            cfg.save_app_state(self.controller.app_state)

            self._update_profile_list(name)
            logger.info(f"Persistence: Profile '{name}' saved successfully.")
            mb.showinfo(i18n.t("gui.dialogs.saved_title"), i18n.t("gui.profiles.saved", name=name))

    def delete_profile(self) -> None:
        """
        Remove a configuration preset from the persistent state.
        """
        view = self.controller.settings_view
        name = view.combo_profiles.get()

        if name == i18n.t("gui.profiles.no_selection"):
            return

        profiles = self.controller.app_state.get("saved_profiles", {})
        if name in profiles:
            confirm = mb.askyesno(
                i18n.t("gui.dialogs.confirm_title"),
                i18n.t("gui.profiles.confirm_delete", name=name)
            )
            if confirm:
                del profiles[name]
                cfg.save_app_state(self.controller.app_state)
                self._update_profile_list()
                logger.info(f"Persistence: Profile '{name}' deleted.")

    # -----------------------------------------------------------------------------
    # INTERNAL UI SYNCHRONIZERS
    # -----------------------------------------------------------------------------

    def _update_profile_list(self, select_name: str = "") -> None:
        """
        Refresh the available profiles in the UI ComboBox.

        Args:
            select_name: Optional profile name to set as current selection.
        """
        view = self.controller.settings_view
        names = sorted(list(self.controller.app_state.get("saved_profiles", {}).keys()))
        view.combo_profiles.configure(values=names)

        if select_name:
            view.combo_profiles.set(select_name)
        else:
            view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))