from __future__ import annotations

"""
Advanced Settings UI Component.

Constructs the configuration management panel. Provides interfaces for 
profile persistence (save/load/delete), extension stack selection, 
AI model provider mapping, and granular processing filters.
"""

import logging
from typing import Dict, Any, List

import customtkinter as ctk

from transcriptor4ai.domain import constants as const
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# SETTINGS VIEW CLASS
# -----------------------------------------------------------------------------

class SettingsFrame(ctk.CTkFrame):
    """
    Configuration and Profiles management view.

    Coordinates multiple sub-sections for complex application settings,
    utilizing a scrollable layout for organized access to filters and
    model selection.
    """

    def __init__(self, master: Any, config: Dict[str, Any], profile_names: List[str], **kwargs: Any):
        """
        Initialize the settings view with state and profile metadata.

        Args:
            master: Parent UI container.
            config: Active session state for widget population.
            profile_names: Collection of available named configurations.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # -----------------------------------------------------------------------------
        # LAYOUT: SCROLLABLE SETTINGS CONTAINER
        # -----------------------------------------------------------------------------
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # -----------------------------------------------------------------------------
        # SECTION 1: PROFILE MANAGEMENT
        # -----------------------------------------------------------------------------
        self.frame_profiles = ctk.CTkFrame(self.scroll)
        self.frame_profiles.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            self.frame_profiles,
            text=i18n.t("gui.labels.profile"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_profiles = ctk.CTkComboBox(
            self.frame_profiles,
            values=profile_names,
            state="readonly"
        )
        self.combo_profiles.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.btn_load = ctk.CTkButton(self.frame_profiles, text=i18n.t("gui.profiles.load"), width=60)
        self.btn_load.pack(side="left", padx=5)
        self.btn_save = ctk.CTkButton(self.frame_profiles, text=i18n.t("gui.profiles.save"), width=60)
        self.btn_save.pack(side="left", padx=5)
        self.btn_del = ctk.CTkButton(
            self.frame_profiles, text=i18n.t("gui.profiles.del"),
            width=60, fg_color="#E04F5F"
        )
        self.btn_del.pack(side="left", padx=5)

        # -----------------------------------------------------------------------------
        # SECTION 2: TECHNOLOGY STACK PRESETS
        # -----------------------------------------------------------------------------
        self.frame_stack = ctk.CTkFrame(self.scroll)
        self.frame_stack.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(
            self.frame_stack,
            text=i18n.t("gui.settings.stack_header"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_stack = ctk.CTkComboBox(
            self.frame_stack,
            values=[i18n.t("gui.combos.select_stack")] + sorted(list(const.DEFAULT_STACKS.keys())),
            width=300,
            state="readonly"
        )
        self.combo_stack.pack(padx=10, pady=10, anchor="w", fill="x")

        # -----------------------------------------------------------------------------
        # SECTION 3: AI INFRASTRUCTURE (PROVIDER & MODEL)
        # -----------------------------------------------------------------------------
        self.frame_ai = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.frame_ai.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.frame_ai.grid_columnconfigure((0, 1), weight=1)

        # Sub-Section: Provider Selection
        self.frame_provider = ctk.CTkFrame(self.frame_ai)
        self.frame_provider.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(
            self.frame_provider,
            text=i18n.t("gui.settings.provider_label", default="AI Provider"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_provider = ctk.CTkComboBox(
            self.frame_provider,
            values=[],
            width=200,
            state="readonly"
        )
        self.combo_provider.pack(padx=10, pady=10, anchor="w", fill="x")

        # Sub-Section: Model Resolution
        self.frame_model = ctk.CTkFrame(self.frame_ai)
        self.frame_model.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(
            self.frame_model,
            text=i18n.t("gui.settings.model_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_model = ctk.CTkComboBox(
            self.frame_model,
            values=[],
            width=200,
            state="readonly"
        )
        self.combo_model.set(config.get("target_model", const.DEFAULT_MODEL_KEY))
        self.combo_model.pack(padx=10, pady=10, anchor="w", fill="x")

        # -----------------------------------------------------------------------------
        # SECTION 4: PIPELINE FILTERS (REGEX & EXTENSIONS)
        # -----------------------------------------------------------------------------
        self.frame_filters = ctk.CTkFrame(self.scroll)
        self.frame_filters.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.frame_filters.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_filters, text=i18n.t("gui.labels.extensions")).grid(row=0, column=0, padx=10, pady=10,
                                                                                    sticky="w")
        self.entry_ext = ctk.CTkEntry(self.frame_filters)
        self.entry_ext.insert(0, ",".join(config.get("extensions", [])))
        self.entry_ext.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_filters, text=i18n.t("gui.labels.include")).grid(row=1, column=0, padx=10, pady=10,
                                                                                 sticky="w")
        self.entry_inc = ctk.CTkEntry(self.frame_filters)
        self.entry_inc.insert(0, ",".join(config.get("include_patterns", [])))
        self.entry_inc.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_filters, text=i18n.t("gui.labels.exclude")).grid(row=2, column=0, padx=10, pady=10,
                                                                                 sticky="w")
        self.entry_exc = ctk.CTkEntry(self.frame_filters)
        self.entry_exc.insert(0, ",".join(config.get("exclude_patterns", [])))
        self.entry_exc.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.sw_gitignore = ctk.CTkSwitch(self.frame_filters, text=i18n.t("gui.checkboxes.gitignore"))
        if config.get("respect_gitignore"): self.sw_gitignore.select()
        self.sw_gitignore.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # -----------------------------------------------------------------------------
        # SECTION 5: OUTPUT ARCHITECTURE & DATA SECURITY
        # -----------------------------------------------------------------------------
        self.frame_fmt = ctk.CTkFrame(self.scroll)
        self.frame_fmt.grid(row=4, column=0, sticky="ew", pady=(0, 10))

        # Output Strategy Toggles
        ctk.CTkLabel(
            self.frame_fmt,
            text=i18n.t("gui.settings.output_strat"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.sw_individual = ctk.CTkSwitch(self.frame_fmt, text=i18n.t("gui.checkboxes.individual"))
        if config.get("create_individual_files"): self.sw_individual.select()
        self.sw_individual.pack(anchor="w", padx=10, pady=5)

        self.sw_unified = ctk.CTkSwitch(self.frame_fmt, text=i18n.t("gui.checkboxes.unified"))
        if config.get("create_unified_file"): self.sw_unified.select()
        self.sw_unified.pack(anchor="w", padx=10, pady=5)

        # Security and Content Optimization Toggles
        ctk.CTkLabel(
            self.frame_fmt,
            text=i18n.t("gui.settings.security"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        self.sw_sanitizer = ctk.CTkSwitch(self.frame_fmt, text="Sanitize Secrets (Redact Keys/IPs)")
        if config.get("enable_sanitizer"): self.sw_sanitizer.select()
        self.sw_sanitizer.pack(anchor="w", padx=10, pady=5)

        self.sw_mask = ctk.CTkSwitch(self.frame_fmt, text="Mask User Paths")
        if config.get("mask_user_paths"): self.sw_mask.select()
        self.sw_mask.pack(anchor="w", padx=10, pady=5)

        self.sw_minify = ctk.CTkSwitch(self.frame_fmt, text="Minify Code (Remove Comments)")
        if config.get("minify_output"): self.sw_minify.select()
        self.sw_minify.pack(anchor="w", padx=10, pady=5)

        # -----------------------------------------------------------------------------
        # SECTION 6: SYSTEM UTILITIES & RESET
        # -----------------------------------------------------------------------------
        self.sw_error_log = ctk.CTkSwitch(self.frame_fmt, text=i18n.t("gui.checkboxes.log_err"))
        if config.get("save_error_log"): self.sw_error_log.select()
        self.sw_error_log.pack(anchor="w", padx=10, pady=5)

        self.btn_reset = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.buttons.reset"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_reset.grid(row=5, column=0, pady=20, padx=10)