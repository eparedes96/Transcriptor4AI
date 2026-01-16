from __future__ import annotations

from typing import Any

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.utils.i18n import i18n


class SidebarFrame(ctk.CTkFrame):
    """
    Left navigation panel containing branding, menu buttons, and update badges.
    """

    def __init__(self, master: Any, nav_callback: Any, **kwargs: Any):
        super().__init__(master, width=200, corner_radius=0, **kwargs)

        self.nav_callback = nav_callback

        # 1. Branding / Logo
        self.logo_label = ctk.CTkLabel(
            self,
            text="Transcriptor\n4AI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.version_label = ctk.CTkLabel(
            self,
            text=f"v{cfg.CURRENT_CONFIG_VERSION}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # 2. Navigation Buttons
        self.btn_dashboard = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.dashboard"),
            command=lambda: self.nav_callback("dashboard"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.settings"),
            command=lambda: self.nav_callback("settings"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10)

        self.btn_logs = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.logs"),
            command=lambda: self.nav_callback("logs"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_logs.grid(row=4, column=0, padx=20, pady=10)

        # 3. Update Badge (Hidden by default)
        self.update_badge = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.update"),
            fg_color="#2CC985",
            hover_color="#229965",
            state="disabled",
            text_color="white"
        )

        # Spacer to push bottom items
        self.grid_rowconfigure(5, weight=1)

        # 4. Footer Buttons
        self.btn_feedback = ctk.CTkButton(
            self,
            text="Feedback",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            height=25,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_feedback.grid(row=6, column=0, padx=20, pady=(0, 10))
