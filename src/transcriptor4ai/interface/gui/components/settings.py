from __future__ import annotations

"""
Advanced Settings UI Component.

Constructs the configuration management panel using a modular composition 
approach. Acts as a layout orchestrator that assembles specialized 
sub-sections (Profiles, AI Models, Filters, Formatting) and provides 
high-level maintenance triggers for cache and state management.
"""

import logging
from typing import Any, Dict, Final, List

import customtkinter as ctk

from transcriptor4ai.interface.gui.components.settings_parts.ai_model_part import AIModelSection
from transcriptor4ai.interface.gui.components.settings_parts.filters_part import FiltersSection
from transcriptor4ai.interface.gui.components.settings_parts.formatting_part import (
    FormattingSection,
)
from transcriptor4ai.interface.gui.components.settings_parts.profiles_part import ProfilesSection
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_WARNING: Final[str] = "#A51F1F"
COLOR_WARNING_HOVER: Final[str] = "#7A1616"
COLOR_SECONDARY: Final[str] = "#DCE4EE"


# ==============================================================================
# VIEW COMPONENT: SETTINGS FRAME
# ==============================================================================

class SettingsFrame(ctk.CTkFrame):
    """
    Configuration and Profiles management view.

    Orchestrates multiple specialized sub-sections for complex application
    settings, utilizing a scrollable layout to handle vertical overflow.
    """

    def __init__(
        self,
        master: Any,
        config: Dict[str, Any],
        profile_names: List[str],
        **kwargs: Any
    ) -> None:
        """
        Initialize the settings view and its modular sub-components.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        # 1. LAYOUT: Establish primary responsive grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. CONTAINER: Initialize the main scrollable area for setting blocks
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # ==========================================================================
        # MODULAR ASSEMBLY (SECTION INITIALIZATION)
        # ==========================================================================
        # CRITICAL POINT: Sub-sections register their interactive widgets directly
        # onto this frame instance to allow centralized binding in the AppController.

        # 3. PROFILES: Named preset management (Save/Load/Delete)
        ProfilesSection(self, self.scroll, profile_names)

        # 4. STACKS: Quick technology-specific extension presets
        _StackSection(self, self.scroll)

        # 5. AI CONTEXT: Provider and Model selection (Dynamic lists)
        AIModelSection(self, self.scroll, config)

        # 6. DISCOVERY: File extensions and regex pattern filters
        FiltersSection(self, self.scroll, config)

        # 7. OUTPUT: Formatting, security, and optimization flags
        FormattingSection(self, self.scroll, config)

        # 8. FOOTER: Construct maintenance and reset triggers
        self._build_action_footer(self.scroll)

    # ==========================================================================
    # INTERNAL BUILDERS
    # ==========================================================================

    def _build_action_footer(self, container: ctk.CTkScrollableFrame) -> None:
        """Construct the bottom area for global state actions."""
        # 1. SETUP: Frame container for footer buttons
        frame_actions = ctk.CTkFrame(container, fg_color="transparent")
        frame_actions.grid(row=5, column=0, sticky="ew", pady=20, padx=10)
        frame_actions.grid_columnconfigure((0, 1), weight=1)

        # 2. ACTION: Cache purge trigger (Maintenance)
        self.btn_purge = ctk.CTkButton(
            frame_actions,
            text="Purge Cache",
            fg_color=COLOR_WARNING,
            hover_color=COLOR_WARNING_HOVER,
            text_color="white",
            width=140
        )
        self.btn_purge.grid(row=0, column=0, padx=10, sticky="e")

        # 3. ACTION: Global configuration reset (Domain defaults)
        self.btn_reset = ctk.CTkButton(
            frame_actions,
            text=i18n.t("gui.buttons.reset"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", COLOR_SECONDARY),
            width=140
        )
        self.btn_reset.grid(row=0, column=1, padx=10, sticky="w")


# ==============================================================================
# INTERNAL HELPER COMPONENTS
# ==============================================================================

class _StackSection:
    """
    Handles the UI for selecting technology-specific extension presets.

    This component is kept internal as a private helper for the settings
    orchestrator due to its single-widget logic.
    """

    def __init__(self, master: SettingsFrame, container: ctk.CTkScrollableFrame) -> None:
        """
        Initialize the stack preset selection group.
        """
        # 1. SETUP: Section frame
        frame = ctk.CTkFrame(container)
        frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # 2. LABEL: Identification
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.settings.stack_header"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # 3. OPTIONS: Resolve available stacks from domain constants
        stacks = [i18n.t("gui.combos.select_stack")] + sorted(list(const.DEFAULT_STACKS.keys()))

        # 4. WIDGET: Register ComboBox on the master for Controller access
        master.combo_stack = ctk.CTkComboBox(
            frame,
            values=stacks,
            width=300,
            state="readonly"
        )
        master.combo_stack.pack(padx=10, pady=10, anchor="w", fill="x")