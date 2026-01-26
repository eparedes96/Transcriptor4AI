from __future__ import annotations

"""
Profile Management UI Section.

Constructs the visual component for managing named configuration presets 
(profiles). Handles the registration of selection and action widgets 
(Load, Save, Delete) within the Settings layout to facilitate 
dynamic session switching.
"""

import logging
from typing import TYPE_CHECKING, Final, List

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to resolve circular dependencies during static analysis
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
# Standardized danger color for destructive actions (Delete)
COLOR_DANGER: Final[str] = "#E04F5F"


# ==============================================================================
# VIEW COMPONENT: PROFILES SECTION
# ==============================================================================

class ProfilesSection:
    """
    Sub-view component for the SettingsFrame handling configuration presets.

    Attributes are registered directly on the master (SettingsFrame) to allow
    the ProfileController and FormBinder to interact with them without
    deep hierarchy traversal.
    """

    def __init__(
        self,
        master: SettingsFrame,
        container: ctk.CTkScrollableFrame,
        profile_names: List[str]
    ) -> None:
        """
        Initialize the profiles layout and register functional widgets.

        Args:
            master: The parent SettingsFrame instance (Dependency Container).
            container: The visual layout manager (Scrollable Frame).
            profile_names: Alphabetical list of existing profile identifiers.
        """
        # 1. SETUP: Create the section container frame for profile actions
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        # 2. LABELS: Header for the Profile Management section
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.labels.profile"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # ======================================================================
        # PROFILE SELECTION & ACTIONS
        # ======================================================================

        # 3. SELECTION: ComboBox for choosing between existing presets
        master.combo_profiles = ctk.CTkComboBox(
            self.frame,
            values=profile_names,
            state="readonly"
        )
        master.combo_profiles.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        # 4. ACTION: Profile Activation (Load)
        master.btn_load = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.profiles.load"),
            width=60
        )
        master.btn_load.pack(side="left", padx=5)

        # 5. ACTION: Profile Persistence (Save As)
        master.btn_save = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.profiles.save"),
            width=60
        )
        master.btn_save.pack(side="left", padx=5)

        # 6. ACTION: Destructive Profile Removal (Delete)
        master.btn_del = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.profiles.del"),
            width=60,
            fg_color=COLOR_DANGER
        )
        master.btn_del.pack(side="left", padx=5)

        logger.debug("UI: ProfilesSection successfully initialized and registered.")