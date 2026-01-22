from __future__ import annotations

from typing import TYPE_CHECKING

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame

class CostSection:
    """Handles financial estimation display and network status indicators."""

    def __init__(self, master: DashboardFrame, container: ctk.CTkScrollableFrame) -> None:
        master.frame_cost = ctk.CTkFrame(container)
        master.frame_cost.grid(row=3, column=0, sticky="ew", pady=(10, 10))
        master.frame_cost.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            master.frame_cost,
            text=i18n.t("gui.dashboard.cost_label", default="Estimated Cost:"),
            font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        master.lbl_cost_val = ctk.CTkLabel(
            master.frame_cost,
            text="$0.0000",
            font=ctk.CTkFont(family="Consolas", size=14, weight="bold"),
            text_color="green"
        )
        master.lbl_cost_val.grid(row=0, column=1, padx=10, pady=10, sticky="w")

        master.lbl_pricing_status = ctk.CTkLabel(
            master.frame_cost,
            text="Initializing...",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        master.lbl_pricing_status.grid(row=0, column=2, padx=10, pady=10, sticky="e")