from __future__ import annotations

"""
UI Section for Formatting and Security.

Manages output strategies (individual vs. unified), secret redaction 
(sanitization), local path masking, and code optimization (minification).
"""

from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame


class FormattingSection:
    """
    Handles output file strategies, security redaction, and optimization toggles.
    """

    def __init__(
            self,
            master: SettingsFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the formatting section and register widgets in the master.

        Args:
            master: The parent SettingsFrame for widget registration.
            container: The scrollable frame for layout placement.
            config: Active session state for initial values.
        """
        frame = ctk.CTkFrame(container)
        frame.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        # --- Output Strategy Sub-Section ---
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.settings.output_strat"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        master.sw_individual = ctk.CTkSwitch(frame, text=i18n.t("gui.checkboxes.individual"))
        if config.get("create_individual_files"):
            master.sw_individual.select()
        master.sw_individual.pack(anchor="w", padx=10, pady=5)

        master.sw_unified = ctk.CTkSwitch(frame, text=i18n.t("gui.checkboxes.unified"))
        if config.get("create_unified_file"):
            master.sw_unified.select()
        master.sw_unified.pack(anchor="w", padx=10, pady=5)

        # --- Security & Optimization Sub-Section ---
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.settings.security"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        master.sw_sanitizer = ctk.CTkSwitch(frame, text="Sanitize Secrets (Redact Keys/IPs)")
        if config.get("enable_sanitizer"):
            master.sw_sanitizer.select()
        master.sw_sanitizer.pack(anchor="w", padx=10, pady=5)

        master.sw_mask = ctk.CTkSwitch(frame, text="Mask User Paths")
        if config.get("mask_user_paths"):
            master.sw_mask.select()
        master.sw_mask.pack(anchor="w", padx=10, pady=5)

        master.sw_minify = ctk.CTkSwitch(frame, text="Minify Code (Remove Comments)")
        if config.get("minify_output"):
            master.sw_minify.select()
        master.sw_minify.pack(anchor="w", padx=10, pady=5)

        master.sw_error_log = ctk.CTkSwitch(frame, text=i18n.t("gui.checkboxes.log_err"))
        if config.get("save_error_log"):
            master.sw_error_log.select()
        master.sw_error_log.pack(anchor="w", padx=10, pady=5)