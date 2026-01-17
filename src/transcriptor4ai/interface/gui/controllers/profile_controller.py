from __future__ import annotations

"""
Profile Management Controller.

Handles logic for loading, saving, and deleting user configuration profiles.
It interacts with the persistent app state and updates the UI accordingly.
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


class ProfileController:
    """
    Manages the lifecycle of user profiles (Save/Load/Delete).
    """

    def __init__(self, main_controller: AppController):
        self.controller = main_controller

    def load_profile(self) -> None:
        """
        Load selected profile configuration into the active view.
        """
        view = self.controller.settings_view
        name = view.combo_profiles.get()

        if name == i18n.t("gui.profiles.no_selection"):
            return

        profiles = self.controller.app_state.get("saved_profiles", {})
        if name in profiles:
            logger.info(f"Loading profile: {name}")

            # Merge profile data with default config structure to ensure compatibility
            temp = cfg.get_default_config()
            temp.update(profiles[name])

            # Update main config and refresh UI
            self.controller.config.update(temp)
            self.controller.sync_view_from_config()

            # Restore selection (sync resets widgets)
            view.combo_profiles.set(name)
            view.combo_stack.set(i18n.t("gui.combos.select_stack"))

            mb.showinfo(i18n.t("gui.dialogs.success_title"), f"Profile '{name}' loaded.")

    def save_profile(self) -> None:
        """
        Persist current configuration as a named profile.
        """
        dialog = ctk.CTkInputDialog(
            text=i18n.t("gui.profiles.prompt_name"),
            title="Save Profile"
        )
        name = dialog.get_input()

        if name:
            name = name.strip()
            profiles = self.controller.app_state.setdefault("saved_profiles", {})

            # Confirm overwrite if exists
            if name in profiles:
                confirm = mb.askyesno(
                    i18n.t("gui.profiles.confirm_overwrite_title"),
                    i18n.t("gui.profiles.confirm_overwrite_msg", name=name)
                )
                if not confirm:
                    return

            # Scrape current UI state to config before saving
            self.controller.sync_config_from_view()

            # Save deep copy of config
            profiles[name] = self.controller.config.copy()
            cfg.save_app_state(self.controller.app_state)

            self._update_profile_list(name)
            logger.info(f"Profile saved: {name}")
            mb.showinfo(i18n.t("gui.dialogs.saved_title"), i18n.t("gui.profiles.saved", name=name))

    def delete_profile(self) -> None:
        """
        Remove the currently selected profile.
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
                logger.info(f"Profile deleted: {name}")

    def _update_profile_list(self, select_name: str = "") -> None:
        """
        Refresh the ComboBox options from the app state.

        Args:
            select_name: If provided, select this profile. Otherwise default to None.
        """
        view = self.controller.settings_view
        names = sorted(list(self.controller.app_state.get("saved_profiles", {}).keys()))
        view.combo_profiles.configure(values=names)

        if select_name:
            view.combo_profiles.set(select_name)
        else:
            view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))