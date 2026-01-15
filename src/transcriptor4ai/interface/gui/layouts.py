from __future__ import annotations

"""
CustomTkinter Layout Definitions.

This module acts as the 'View' layer. It defines the structural components
of the application using a modern, object-oriented approach.

Components:
- SidebarFrame: Navigation and branding.
- DashboardFrame: Main operational area (IO, Stacks, Actions).
- SettingsFrame: Configuration, Filters, and Profiles.
- LogsFrame: Read-only console for application logs.
"""

import logging
from typing import Dict, Any, List

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# =============================================================================
# Sidebar (Navigation)
# =============================================================================
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


## =============================================================================
# Dashboard (Main Operations)
# =============================================================================
class DashboardFrame(ctk.CTkFrame):
    """
    Main workspace: IO paths, Action buttons.
    Wrapped in ScrollableFrame for small screens.
    """

    def __init__(self, master: Any, config: Dict[str, Any], **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scroll container
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # --- Section 1: Input / Output ---
        self.frame_io = ctk.CTkFrame(self.scroll)
        self.frame_io.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame_io.grid_columnconfigure(0, weight=1)

        # Input Header
        ctk.CTkLabel(
            self.frame_io,
            text=i18n.t("gui.dashboard.source_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # Input Controls
        self.entry_input = ctk.CTkEntry(self.frame_io, placeholder_text="/path/to/project")
        self.entry_input.insert(0, config.get("input_path", ""))
        self.entry_input.configure(state="readonly")
        self.entry_input.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        self.btn_browse_in = ctk.CTkButton(
            self.frame_io,
            text=i18n.t("gui.buttons.explore"),
            width=80
        )
        self.btn_browse_in.grid(row=1, column=1, padx=10, pady=10)

        # Output Header
        ctk.CTkLabel(
            self.frame_io,
            text=i18n.t("gui.dashboard.dest_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # Output Controls
        self.entry_output = ctk.CTkEntry(self.frame_io, placeholder_text="/path/to/output")
        self.entry_output.insert(0, config.get("output_base_dir", ""))
        self.entry_output.configure(state="readonly")
        self.entry_output.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        self.btn_browse_out = ctk.CTkButton(
            self.frame_io,
            text=i18n.t("gui.buttons.examine"),
            width=80
        )
        self.btn_browse_out.grid(row=3, column=1, padx=10, pady=10)

        # Subdir & Prefix Headers
        self.frame_sub_headers = ctk.CTkFrame(self.frame_io, fg_color="transparent")
        self.frame_sub_headers.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10)

        ctk.CTkLabel(
            self.frame_sub_headers,
            text=i18n.t("gui.labels.subdir"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray60")
        ).pack(side="left", padx=(0, 100))

        ctk.CTkLabel(
            self.frame_sub_headers,
            text=i18n.t("gui.labels.prefix"),
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray40", "gray60")
        ).pack(side="left")

        # Subdir & Prefix Inputs
        self.frame_sub = ctk.CTkFrame(self.frame_io, fg_color="transparent")
        self.frame_sub.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        self.entry_subdir = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Subdir")
        self.entry_subdir.insert(0, config.get("output_subdir_name", ""))
        self.entry_subdir.pack(side="left", padx=(0, 10))

        self.entry_prefix = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Prefix")
        self.entry_prefix.insert(0, config.get("output_prefix", ""))
        self.entry_prefix.pack(side="left")

        # --- Section 2: Quick Toggles ---
        self.frame_opts = ctk.CTkFrame(self.scroll)
        self.frame_opts.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame_opts.grid_columnconfigure((0, 1, 2), weight=1)

        self.sw_modules = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.modules"))
        if config.get("process_modules"): self.sw_modules.select()
        self.sw_modules.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.sw_tests = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.tests"))
        if config.get("process_tests"): self.sw_tests.select()
        self.sw_tests.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        self.sw_resources = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.resources"))
        if config.get("process_resources"): self.sw_resources.select()
        self.sw_resources.grid(row=0, column=2, padx=20, pady=15, sticky="w")

        # Tree Toggle
        self.sw_tree = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.gen_tree"))
        if config.get("generate_tree"): self.sw_tree.select()
        self.sw_tree.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        # --- AST Options Sub-Frame ---
        self.frame_ast = ctk.CTkFrame(self.scroll, fg_color="transparent")

        self.chk_func = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_func"))
        if config.get("show_functions"): self.chk_func.select()
        self.chk_func.pack(side="left", padx=20)

        self.chk_class = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_class"))
        if config.get("show_classes"): self.chk_class.select()
        self.chk_class.pack(side="left", padx=20)

        self.chk_meth = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_meth"))
        if config.get("show_methods"): self.chk_meth.select()
        self.chk_meth.pack(side="left", padx=20)

        # --- Section 3: Action Bar ---
        self.btn_process = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.dashboard.btn_start"),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#007ACC"
        )
        self.btn_process.grid(row=3, column=0, sticky="ew", pady=20, padx=10)

        self.btn_simulate = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.buttons.simulate"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_simulate.grid(row=4, column=0, sticky="ew", padx=10)


# =============================================================================
# Settings (Configuration)
# =============================================================================
class SettingsFrame(ctk.CTkFrame):
    """
    Advanced configuration: Profiles, Filters, Formatting.
    Wrapped in ScrollableFrame for small screens.
    """

    def __init__(self, master: Any, config: Dict[str, Any], profile_names: List[str], **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main scroll container
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # 1. Profiles
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
        self.btn_del = ctk.CTkButton(self.frame_profiles, text=i18n.t("gui.profiles.del"), width=60,
                                     fg_color="#D9534F", hover_color="#C9302C")
        self.btn_del.pack(side="left", padx=5)

        # 2. Selection Container
        self.frame_selection = ctk.CTkFrame(self.scroll, fg_color="transparent")
        self.frame_selection.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame_selection.grid_columnconfigure((0, 1), weight=1)

        # 2a. Quick Stack Presets
        self.frame_stack = ctk.CTkFrame(self.frame_selection)
        self.frame_stack.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        ctk.CTkLabel(
            self.frame_stack,
            text=i18n.t("gui.settings.stack_header"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_stack = ctk.CTkComboBox(
            self.frame_stack,
            values=[i18n.t("gui.combos.select_stack")] + sorted(list(cfg.DEFAULT_STACKS.keys())),
            width=250,
            state="readonly"
        )
        self.combo_stack.pack(padx=10, pady=10, anchor="w", fill="x")

        # 2b. Model Selector
        self.frame_model = ctk.CTkFrame(self.frame_selection)
        self.frame_model.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        ctk.CTkLabel(
            self.frame_model,
            text=i18n.t("gui.settings.model_label"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=5)

        self.combo_model = ctk.CTkComboBox(
            self.frame_model,
            values=sorted(list(cfg.AI_MODELS.keys())),
            width=250,
            state="readonly"
        )
        self.combo_model.set(config.get("target_model", cfg.DEFAULT_MODEL_KEY))
        self.combo_model.pack(padx=10, pady=10, anchor="w", fill="x")

        # 3. Filters
        self.frame_filters = ctk.CTkFrame(self.scroll)
        self.frame_filters.grid(row=2, column=0, sticky="ew", pady=(0, 10))
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

        # 4. Formatting & Security
        self.frame_fmt = ctk.CTkFrame(self.scroll)
        self.frame_fmt.grid(row=3, column=0, sticky="ew", pady=(0, 10))

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

        ctk.CTkLabel(
            self.frame_fmt,
            text=i18n.t("gui.settings.security"),
            font=ctk.CTkFont(weight="bold")
        ).pack(anchor="w", padx=10, pady=(15, 5))

        # Security switches
        self.sw_sanitizer = ctk.CTkSwitch(self.frame_fmt, text="Sanitize Secrets (Redact Keys/IPs)")
        if config.get("enable_sanitizer"): self.sw_sanitizer.select()
        self.sw_sanitizer.pack(anchor="w", padx=10, pady=5)

        self.sw_mask = ctk.CTkSwitch(self.frame_fmt, text="Mask User Paths")
        if config.get("mask_user_paths"): self.sw_mask.select()
        self.sw_mask.pack(anchor="w", padx=10, pady=5)

        self.sw_minify = ctk.CTkSwitch(self.frame_fmt, text="Minify Code (Remove Comments)")
        if config.get("minify_output"): self.sw_minify.select()
        self.sw_minify.pack(anchor="w", padx=10, pady=5)

        # Save Error Log
        self.sw_error_log = ctk.CTkSwitch(self.frame_fmt, text=i18n.t("gui.checkboxes.log_err"))
        if config.get("save_error_log"): self.sw_error_log.select()
        self.sw_error_log.pack(anchor="w", padx=10, pady=5)

        # Reset Config Button
        self.btn_reset = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.buttons.reset"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_reset.grid(row=4, column=0, pady=20, padx=10)


# =============================================================================
# Logs Console
# =============================================================================
class LogsFrame(ctk.CTkFrame):
    """
    Read-only console to display system logs in the UI.
    """

    def __init__(self, master: Any, **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.textbox = ctk.CTkTextbox(self, state="disabled", font=("Consolas", 10))
        self.textbox.grid(row=0, column=0, sticky="nsew")

        self.btn_copy = ctk.CTkButton(
            self,
            text=i18n.t("gui.logs.copy"),
            command=self._copy_logs
        )
        self.btn_copy.grid(row=1, column=0, pady=10, sticky="e")

    def append_log(self, msg: str) -> None:
        self.textbox.configure(state="normal")
        self.textbox.insert("end", msg + "\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def _copy_logs(self) -> None:
        self.master.clipboard_clear()
        self.master.clipboard_append(self.textbox.get("1.0", "end"))


# =============================================================================
# Main Window Factory
# =============================================================================
def create_main_window(
        profile_names: List[str],
        config: Dict[str, Any]
) -> ctk.CTk:
    """
    Factory to create the root CustomTkinter application window.
    It prepares the layout but does NOT start the loop.

    Args:
        profile_names: List of available profiles.
        config: Initial configuration dict.

    Returns:
        ctk.CTk: The configured root window object (with Frames attached).
    """
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()

    app.title(f"Transcriptor4AI - v{cfg.CURRENT_CONFIG_VERSION}")
    app.geometry("1000x700")

    # Configure Grid Layout (1 Sidebar + 1 Content)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    return app