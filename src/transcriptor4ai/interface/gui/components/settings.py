from __future__ import annotations

"""
Advanced Settings UI Component.

Constructs the configuration management panel using a modular approach. 
Acts as a layout orchestrator that assembles specialized sub-sections 
imported from the settings_parts package.
"""

import logging
from typing import Any, Dict, List

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.interface.gui.components.settings_parts.ai_model_part import AIModelSection
from transcriptor4ai.interface.gui.components.settings_parts.filters_part import FiltersSection
from transcriptor4ai.interface.gui.components.settings_parts.formatting_part import (
    FormattingSection,
)
from transcriptor4ai.interface.gui.components.settings_parts.profiles_part import ProfilesSection
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# ==============================================================================
# SETTINGS VIEW COMPONENT
# ==============================================================================

class SettingsFrame(ctk.CTkFrame):
    """
    Configuration and Profiles management view.

    Orchestrates multiple specialized sub-sections for complex application
    settings, utilizing a scrollable layout.
    """

    def __init__(
            self,
            master: Any,
            config: Dict[str, Any],
            profile_names: List[str],
            **kwargs: Any
    ):
        """
        Initialize the settings view and its modular sub-components.

        Args:
            master: Parent UI container.
            config: Active session state for widget population.
            profile_names: Collection of available named configurations.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scrollable container for settings sections
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # --- Section Initialization (Modular Assembly) ---
        ProfilesSection(self, self.scroll, profile_names)
        _StackSection(self, self.scroll)
        AIModelSection(self, self.scroll, config)
        FiltersSection(self, self.scroll, config)
        FormattingSection(self, self.scroll, config)

        # --- Global Action Footer ---
        self.btn_reset = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.buttons.reset"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_reset.grid(row=5, column=0, pady=20, padx=10)


# ==============================================================================
# PRIVATE LAYOUT HELPERS
# ==============================================================================

class _StackSection:
    """
    Handles the UI for selecting technology-specific extension presets.

    This component remains internal as it is a single widget group
    with minimal logic.
    """

    def __init__(self, master: SettingsFrame, container: ctk.CTkScrollableFrame) -> None:
        """
        Initialize the stack preset selection group.

        Args:
            master: Parent SettingsFrame for widget registration.
            container: Placement container.
        """
        frame = ctk.CTkFrame(container)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.settings.stack_header"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        stacks = [i18n.t("gui.combos.select_stack")] + sorted(list(const.DEFAULT_STACKS.keys()))

        master.combo_stack = ctk.CTkComboBox(
            frame,
            values=stacks,
            width=300,
            state="readonly"
        )
        master.combo_stack.pack(padx=10, pady=10, anchor="w", fill="x")