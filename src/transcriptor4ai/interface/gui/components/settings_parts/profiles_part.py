from __future__ import annotations

"""
UI Section for Profile Management.

Provides the visual components and widget registration for loading, 
saving, and deleting configuration presets within the settings view.
"""

from typing import TYPE_CHECKING, List

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame


class ProfilesSection:
    """
    Handles the UI for loading, saving, and deleting configuration profiles.
    """

    def __init__(
            self,
            master: SettingsFrame,
            container: ctk.CTkScrollableFrame,
            profile_names: List[str]
    ) -> None:
        """
        Initialize the profiles section and register widgets in the master.

        Args:
            master: The parent SettingsFrame where widgets will be registered.
            container: The scrollable container for layout placement.
            profile_names: Initial list of available profile identifiers.
        """
        frame = ctk.CTkFrame(container)
        frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.labels.profile"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # Widget registration in master for controller access
        master.combo_profiles = ctk.CTkComboBox(
            frame,
            values=profile_names,
            state="readonly"
        )
        master.combo_profiles.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        master.btn_load = ctk.CTkButton(
            frame,
            text=i18n.t("gui.profiles.load"),
            width=60
        )
        master.btn_load.pack(side="left", padx=5)

        master.btn_save = ctk.CTkButton(
            frame,
            text=i18n.t("gui.profiles.save"),
            width=60
        )
        master.btn_save.pack(side="left", padx=5)

        master.btn_del = ctk.CTkButton(
            frame,
            text=i18n.t("gui.profiles.del"),
            width=60,
            fg_color="#E04F5F"
        )
        master.btn_del.pack(side="left", padx=5)