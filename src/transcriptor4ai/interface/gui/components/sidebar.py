from __future__ import annotations

"""
Sidebar Navigation Component.

Defines the persistent left-hand panel of the application. Manages high-level 
routing, branding display, and dynamic update notifications. Acts as the 
anchor for the main window layout.
"""

import logging
from typing import Any, Callable, Final

import customtkinter as ctk

from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_UPDATE: Final[str] = "#E04F5F"
COLOR_UPDATE_HOVER: Final[str] = "#A03541"
COLOR_SECONDARY_TEXT: Final[str] = ("gray10", "#DCE4EE")


# ==============================================================================
# VIEW COMPONENT: SIDEBAR FRAME
# ==============================================================================

class SidebarFrame(ctk.CTkFrame):
    """
    Application navigation and information sidebar.

    Provides centralized access to application views and displays metadata
    regarding the versioning and available updates.
    """

    def __init__(
        self,
        master: Any,
        nav_callback: Callable[[str], None],
        **kwargs: Any
    ) -> None:
        """
        Initialize the sidebar with branding and navigation triggers.

        Args:
            master: Parent window container.
            nav_callback: Function to execute for view switching (Dashboard/Settings/Logs).
        """
        super().__init__(master, width=200, corner_radius=0, **kwargs)

        self.nav_callback = nav_callback

        # 1. BRANDING: Logo and Version identifiers
        self._setup_branding()

        # 2. NAVIGATION: Primary routing controls
        self._setup_navigation()

        # 3. UPDATES: Notification badge (State managed by UpdateController)
        self._setup_update_system()

        # 4. FOOTER: Secondary actions and feedback
        self._setup_footer()

        logger.debug("Sidebar: UI structure successfully initialized.")

    # ==========================================================================
    # INTERNAL BUILDERS
    # ==========================================================================

    def _setup_branding(self) -> None:
        """Construct the visual identity section."""
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

    def _setup_navigation(self) -> None:
        """Construct the primary navigation menu."""
        # Dashboard Trigger
        self.btn_dashboard = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.dashboard"),
            command=lambda: self.nav_callback("dashboard"),
            fg_color="transparent",
            border_width=2,
            text_color=COLOR_SECONDARY_TEXT
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=10)

        # Settings Trigger
        self.btn_settings = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.settings"),
            command=lambda: self.nav_callback("settings"),
            fg_color="transparent",
            border_width=2,
            text_color=COLOR_SECONDARY_TEXT
        )
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10)

        # Logs Trigger
        self.btn_logs = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.logs"),
            command=lambda: self.nav_callback("logs"),
            fg_color="transparent",
            border_width=2,
            text_color=COLOR_SECONDARY_TEXT
        )
        self.btn_logs.grid(row=4, column=0, padx=20, pady=10)

    def _setup_update_system(self) -> None:
        """Initialize the update notification badge."""
        self.update_badge = ctk.CTkButton(
            self,
            text=i18n.t("gui.sidebar.update"),
            fg_color=COLOR_UPDATE,
            hover_color=COLOR_UPDATE_HOVER,
            state="disabled",
            text_color="white"
        )

    def _setup_footer(self) -> None:
        """Construct the bottom-aligned utilities."""
        # Strategic grid weight to push items following this row to the bottom
        self.grid_rowconfigure(5, weight=1)

        self.btn_feedback = ctk.CTkButton(
            self,
            text="Feedback",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            border_width=1,
            height=25,
            text_color=COLOR_SECONDARY_TEXT
        )
        self.btn_feedback.grid(row=6, column=0, padx=20, pady=(0, 10))