from __future__ import annotations

"""
Dashboard UI Component.

Constructs the primary workspace for the application.
Acts as a Facade that orchestrates specialized sub-sections:
Input, Options, Cost, and Execution Actions.
"""

import logging
from typing import Any, Dict

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
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


class DashboardFrame(ctk.CTkFrame):
    """
    Main execution dashboard for Transcriptor4AI.

    Attributes are dynamically populated by sub-sections (InputSection, etc.)
    to allow direct access by the Controller (Binder).
    """

    def __init__(self, master: Any, config: Dict[str, Any], **kwargs: Any):
        """
        Initialize the dashboard with persistent session configuration.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # 1. Input & Output Paths
        InputSection(self, self.scroll, config)

        # 2. Processing Options & AST
        OptionsSection(self, self.scroll, config)

        # 3. Financial Estimation
        CostSection(self, self.scroll)

        # 4. Action Buttons (Execution)
        self._build_actions(self.scroll)

    def _build_actions(self, container: ctk.CTkScrollableFrame) -> None:
        """Create the main execution triggers."""
        self.btn_process = ctk.CTkButton(
            container,
            text=i18n.t("gui.dashboard.btn_start"),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1F6AA5"
        )
        self.btn_process.grid(row=4, column=0, sticky="ew", pady=(10, 5), padx=10)

        self.btn_simulate = ctk.CTkButton(
            container,
            text=i18n.t("gui.buttons.simulate"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_simulate.grid(row=5, column=0, sticky="ew", padx=10, pady=(0, 20))

    # ==========================================================================
    # PUBLIC UPDATE METHODS (Called by Controllers)
    # ==========================================================================

    def update_cost_display(self, cost: float) -> None:
        """Update the visual cost amount."""
        if hasattr(self, "lbl_cost_val"):
            self.lbl_cost_val.configure(text=f"${cost:.4f}")
            logger.debug(f"UI: Dashboard cost display updated to ${cost:.4f}")

    def set_pricing_status(self, is_live: bool) -> None:
        """Update the indicator showing the source of pricing data."""
        if not hasattr(self, "lbl_pricing_status"):
            return

        if is_live:
            text = f"{i18n.t('gui.dashboard.status_live', default='Live Pricing')} 🟢"
            color = "green"
        else:
            text = f"{i18n.t('gui.dashboard.status_cached', default='Default Pricing')} 🟠"
            color = "#FF8C00"  # Dark Orange

        self.lbl_pricing_status.configure(text=text, text_color=color)
        logger.debug(f"UI: Pricing status updated (Live={is_live})")