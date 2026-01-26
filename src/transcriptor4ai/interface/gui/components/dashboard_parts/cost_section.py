from __future__ import annotations

"""
Cost Estimation UI Section.

Constructs the visual dashboard component responsible for displaying 
real-time financial impact estimates and the synchronization status 
of the LLM pricing database.
"""

import logging
from typing import TYPE_CHECKING, Final

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to resolve circular dependencies during static analysis
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
# Standardized color for financial success/live status
COLOR_LIVE: Final[str] = "green"
COLOR_STALE: Final[str] = "gray"


# ==============================================================================
# VIEW COMPONENT: COST SECTION
# ==============================================================================

class CostSection:
    """
    Sub-view component for the Dashboard that handles financial reporting.

    Attributes are registered directly onto the master (DashboardFrame)
    to facilitate declarative synchronization via the FormBinder.
    """

    def __init__(self, master: DashboardFrame, container: ctk.CTkScrollableFrame) -> None:
        """
        Initialize the cost display frame and its reactive indicators.

        Args:
            master: The parent DashboardFrame instance (UI Hub).
            container: The scrollable layout manager for widget placement.
        """
        # 1. STRUCTURE: Create the main container frame for financial data
        master.frame_cost = ctk.CTkFrame(container)
        master.frame_cost.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        master.frame_cost.grid_columnconfigure(1, weight=1)

        # 2. LABELS: Static identification of the cost field
        ctk.CTkLabel(
            master.frame_cost,
            text=i18n.t("gui.dashboard.cost_label", default="Estimated Cost:"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # 3. METRICS: Dynamic value display for calculated USD impact
        # Uses monospaced font for decimal alignment and green color for readability
        master.lbl_cost_val = ctk.CTkLabel(
            master.frame_cost,
            text="$0.0000",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color=COLOR_LIVE
        )
        master.lbl_cost_val.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        # 4. STATUS: Metadata indicator for data source (Live vs. Cached)
        # Allows users to know if the pricing is up-to-date
        master.lbl_pricing_status = ctk.CTkLabel(
            master.frame_cost,
            text="Initializing...",
            font=ctk.CTkFont(size=10),
            text_color=COLOR_STALE
        )
        master.lbl_pricing_status.grid(row=0, column=2, padx=10, pady=10, sticky="e")

        logger.debug("UI: CostSection successfully registered into Dashboard container.")