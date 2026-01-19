from __future__ import annotations

"""
Sidebar Navigation Component.

Constructs the persistent left navigation panel. Manages primary 
application routing, visual branding, version identification, 
and dynamic update notifications. Acts as the anchor for the global UI state.
"""

import logging
from typing import Any

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# SIDEBAR VIEW CLASS
# -----------------------------------------------------------------------------

class SidebarFrame(ctk.CTkFrame):
    """
    Application navigation and information sidebar.

    Provides centralized access to core views and displays metadata
    regarding the application lifecycle, including versioning and
    available updates.
    """

    def __init__(self, master: Any, nav_callback: Any, **kwargs: Any):
        """
        Initialize the sidebar with branding and navigation triggers.

        Args:
            master: Parent window container.
            nav_callback: Function to execute for view switching.
        """
        super().__init__(master, width=200, corner_radius=0, **kwargs)

        self.nav_callback = nav_callback

        # -----------------------------------------------------------------------------
        # COMPONENT: BRANDING AND VERSIONING
        # -----------------------------------------------------------------------------
        self.logo_label = ctk.CTkLabel(
            self,
            text="Transcriptor\n4AI",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.version_label = ctk.CTkLabel(
            self,
            text=f"v{const.CURRENT_CONFIG_VERSION}",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        )
        self.version_label.grid(row=1, column=0, padx=20, pady=(0, 20))

        # -----------------------------------------------------------------------------
        # COMPONENT: NAVIGATION ROUTING
        # -----------------------------------------------------------------------------
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

        # -----------------------------------------------------------------------------
        # COMPONENT: OTA UPDATE NOTIFICATION
        # -----------------------------------------------------------------------------
        # Initialized as disabled; visibility managed by the update controller
        self.update_badge = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.update"),
            fg_color="#E04F5F",
            hover_color="#A03541",
            state="disabled",
            text_color="white"
        )

        # Strategic grid weight to push footer items to the bottom
        self.grid_rowconfigure(5, weight=1)

        # -----------------------------------------------------------------------------
        # COMPONENT: FOOTER ACTIONS
        # -----------------------------------------------------------------------------
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