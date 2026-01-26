from __future__ import annotations

"""
Formatting and Security UI Section.

Constructs the visual component for managing output strategies (artifact 
aggregation), privacy sanitization, local path masking, and code optimization 
toggles within the Settings interface.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to resolve circular dependencies during static analysis
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW COMPONENT: FORMATTING SECTION
# ==============================================================================

class FormattingSection:
    """
    Sub-view component for the SettingsFrame handling output and security flags.

    Attributes are registered directly on the master (SettingsFrame) to facilitate
    declarative data binding via the FormBinder service.
    """

    def __init__(
        self,
        master: SettingsFrame,
        container: ctk.CTkScrollableFrame,
        config: Dict[str, Any]
    ) -> None:
        """
        Initialize the formatting section layout and bind initial config states.

        Args:
            master: The parent SettingsFrame instance for widget registration.
            container: The scrollable layout manager for placement.
            config: Initial configuration state for value population.
        """
        # 1. SETUP: Create the section container frame
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        # ======================================================================
        # SUB-SECTION: OUTPUT STRATEGY
        # ======================================================================

        # 2. LABELS: Header for file generation strategies
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.settings.output_strat"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        # 3. SWITCHES: Individual vs Unified file generation
        master.sw_individual = ctk.CTkSwitch(
            self.frame,
            text=i18n.t("gui.checkboxes.individual")
        )
        if config.get("create_individual_files"):
            master.sw_individual.select()
        master.sw_individual.pack(anchor="w", padx=10, pady=5)

        master.sw_unified = ctk.CTkSwitch(
            self.frame,
            text=i18n.t("gui.checkboxes.unified")
        )
        if config.get("create_unified_file"):
            master.sw_unified.select()
        master.sw_unified.pack(anchor="w", padx=10, pady=5)

        # ======================================================================
        # SUB-SECTION: SECURITY & OPTIMIZATION
        # ======================================================================

        # 4. LABELS: Header for privacy and code density controls
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.settings.security"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        # 5. SWITCHES: Sanitization, Masking, and Minification
        master.sw_sanitizer = ctk.CTkSwitch(self.frame, text="Sanitize Secrets (Redact Keys/IPs)")
        if config.get("enable_sanitizer"):
            master.sw_sanitizer.select()
        master.sw_sanitizer.pack(anchor="w", padx=10, pady=5)

        master.sw_mask = ctk.CTkSwitch(self.frame, text="Mask User Paths")
        if config.get("mask_user_paths"):
            master.sw_mask.select()
        master.sw_mask.pack(anchor="w", padx=10, pady=5)

        master.sw_minify = ctk.CTkSwitch(self.frame, text="Minify Code (Remove Comments)")
        if config.get("minify_output"):
            master.sw_minify.select()
        master.sw_minify.pack(anchor="w", padx=10, pady=5)

        # 6. DIAGNOSTICS: Error reporting toggle
        master.sw_error_log = ctk.CTkSwitch(
            self.frame,
            text=i18n.t("gui.checkboxes.log_err")
        )
        if config.get("save_error_log"):
            master.sw_error_log.select()
        master.sw_error_log.pack(anchor="w", padx=10, pady=5)

        logger.debug("UI: FormattingSection successfully initialized and registered.")