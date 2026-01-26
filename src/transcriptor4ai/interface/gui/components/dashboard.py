from __future__ import annotations

"""
Dashboard UI Component.

Constructs the primary workspace for the application. Acts as a visual facade 
that orchestrates specialized sub-sections (Input, Options, Cost) and 
main execution triggers, providing a centralized interface for the 
AppController to manage the transcription lifecycle.
"""

import logging
from typing import Any, Dict, Final

import customtkinter as ctk

from transcriptor4ai.interface.gui.components.dashboard_parts.cost_section import (
    CostSection,
)
from transcriptor4ai.interface.gui.components.dashboard_parts.input_section import (
    InputSection,
)
from transcriptor4ai.interface.gui.components.dashboard_parts.options_section import (
    OptionsSection,
)
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_ACCENT: Final[str] = "#1F6AA5"
COLOR_SECONDARY: Final[str] = "#DCE4EE"
COLOR_LIVE: Final[str] = "green"
COLOR_STALE: Final[str] = "#FF8C00"


# ==============================================================================
# VIEW COMPONENT: DASHBOARD FRAME
# ==============================================================================

class DashboardFrame(ctk.CTkFrame):
    """
    Main execution dashboard container.

    Aggregates functional sections and exposes an API for the controller to
    update execution-related metrics and status indicators.
    """

    def __init__(self, master: Any, config: Dict[str, Any], **kwargs: Any) -> None:
        """
        Initialize the dashboard and its modular sub-components.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        # 1. LAYOUT: Establish responsive grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 2. CONTAINER: Initialize scrollable area for multi-section content
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # 3. COMPOSITION: Instantiate specialized sub-views
        # These sections register their widgets directly onto this instance
        InputSection(self, self.scroll, config)
        OptionsSection(self, self.scroll, config)
        CostSection(self, self.scroll)

        # 4. ACTIONS: Build main execution triggers
        self._build_actions(self.scroll)

    # ==========================================================================
    # INTERNAL BUILDERS
    # ==========================================================================

    def _build_actions(self, container: ctk.CTkScrollableFrame) -> None:
        """Construct and place the primary action buttons."""
        # 1. TRIGGER: Main Processing Button
        self.btn_process = ctk.CTkButton(
            container,
            text=i18n.t("gui.dashboard.btn_start"),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLOR_ACCENT
        )
        self.btn_process.grid(row=4, column=0, sticky="ew", pady=(10, 5), padx=10)

        # 2. TRIGGER: Simulation (Dry-Run) Button
        self.btn_simulate = ctk.CTkButton(
            container,
            text=i18n.t("gui.buttons.simulate"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", COLOR_SECONDARY)
        )
        self.btn_simulate.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 20))

    # ==========================================================================
    # PUBLIC UPDATE API (CONTROLLER INTERFACE)
    # ==========================================================================

    def update_cost_display(self, cost: float) -> None:
        """
        Update the visual currency display for estimated token impact.

        Args:
            cost: Calculated USD value.
        """
        if hasattr(self, "lbl_cost_val"):
            self.lbl_cost_val.configure(text=f"${cost:.4f}")
            logger.debug(f"Dashboard: Cost display updated to ${cost:.4f}")

    def set_pricing_status(self, is_live: bool) -> None:
        """
        Update the price discovery indicator based on network sync status.

        Args:
            is_live: True if data is fresh from the remote API.
        """
        if not hasattr(self, "lbl_pricing_status"):
            return

        # 1. RESOLVE: Determine visual cues for the status label
        if is_live:
            text = f"{i18n.t('gui.dashboard.status_live', default='Live Pricing')} 🟢"
            color = COLOR_LIVE
        else:
            text = f"{i18n.t('gui.dashboard.status_cached', default='Default Pricing')} 🟠"
            color = COLOR_STALE

        # 2. APPLY: Update widget state
        self.lbl_pricing_status.configure(text=text, text_color=color)
        logger.debug(f"Dashboard: Pricing metadata status set to Live={is_live}")