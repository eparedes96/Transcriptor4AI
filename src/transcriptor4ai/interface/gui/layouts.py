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
from typing import Dict, Any, List, Optional

import customtkinter as ctk
try:
    from tkinterdnd2 import TkinterDnD
    _DND_AVAILABLE = True
except ImportError:
    _DND_AVAILABLE = False

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# =============================================================================
# CustomTkinter Base Setup
# =============================================================================
class CtkDnDWrapper(ctk.CTk, TkinterDnD.DnDWrapper):
    """
    Wrapper to mix CustomTkinter with TkinterDnD2.
    Allows the main window to accept Drag & Drop events.
    """
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)


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
            text="Dashboard",
            command=lambda: self.nav_callback("dashboard"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_dashboard.grid(row=2, column=0, padx=20, pady=10)

        self.btn_settings = ctk.CTkButton(
            self,
            text="Settings",
            command=lambda: self.nav_callback("settings"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_settings.grid(row=3, column=0, padx=20, pady=10)

        self.btn_logs = ctk.CTkButton(
            self,
            text="System Logs",
            command=lambda: self.nav_callback("logs"),
            fg_color="transparent",
            border_width=2,
            text_color=("gray10", "#DCE4EE")
        )
        self.btn_logs.grid(row=4, column=0, padx=20, pady=10)

        # 3. Update Badge (Hidden by default)
        self.update_badge = ctk.CTkButton(
            self,
            text="Update Ready",
            fg_color="#2CC985",
            hover_color="#229A65",
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
            height=25
        )
        self.btn_feedback.grid(row=6, column=0, padx=20, pady=(0, 10))


# =============================================================================
# Dashboard (Main Operations)
# =============================================================================
class DashboardFrame(ctk.CTkFrame):
    """
    Main workspace: IO paths, Stack selection, Action buttons.
    """
    def __init__(self, master: Any, config: Dict[str, Any], **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(1, weight=1)

        # --- Section 1: Input / Output ---
        self.frame_io = ctk.CTkFrame(self)
        self.frame_io.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.frame_io.grid_columnconfigure(1, weight=1)

        # Input
        ctk.CTkLabel(self.frame_io, text="Source Code:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_input = ctk.CTkEntry(self.frame_io, placeholder_text="/path/to/project")
        self.entry_input.insert(0, config.get("input_path", ""))
        self.entry_input.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
        self.btn_browse_in = ctk.CTkButton(self.frame_io, text="Browse", width=80)
        self.btn_browse_in.grid(row=0, column=2, padx=10, pady=10)

        # Output
        ctk.CTkLabel(self.frame_io, text="Output Dir:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_output = ctk.CTkEntry(self.frame_io, placeholder_text="/path/to/output")
        self.entry_output.insert(0, config.get("output_base_dir", ""))
        self.entry_output.grid(row=1, column=1, padx=10, pady=10, sticky="ew")
        self.btn_browse_out = ctk.CTkButton(self.frame_io, text="Browse", width=80)
        self.btn_browse_out.grid(row=1, column=2, padx=10, pady=10)

        # Subdir & Prefix
        self.frame_sub = ctk.CTkFrame(self.frame_io, fg_color="transparent")
        self.frame_sub.grid(row=2, column=1, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        self.entry_subdir = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Subdir")
        self.entry_subdir.insert(0, config.get("output_subdir_name", ""))
        self.entry_subdir.pack(side="left", padx=(0, 10))

        self.entry_prefix = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Prefix")
        self.entry_prefix.insert(0, config.get("output_prefix", ""))
        self.entry_prefix.pack(side="left")

        # --- Section 2: Quick Toggles ---
        self.frame_opts = ctk.CTkFrame(self)
        self.frame_opts.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        self.frame_opts.grid_columnconfigure((0, 1, 2), weight=1)

        self.sw_modules = ctk.CTkSwitch(self.frame_opts, text="Modules (Source)")
        if config.get("process_modules"): self.sw_modules.select()
        self.sw_modules.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        self.sw_tests = ctk.CTkSwitch(self.frame_opts, text="Tests")
        if config.get("process_tests"): self.sw_tests.select()
        self.sw_tests.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        self.sw_resources = ctk.CTkSwitch(self.frame_opts, text="Resources")
        if config.get("process_resources"): self.sw_resources.select()
        self.sw_resources.grid(row=0, column=2, padx=20, pady=15, sticky="w")

        self.sw_tree = ctk.CTkSwitch(self.frame_opts, text="Generate Tree")
        if config.get("generate_tree"): self.sw_tree.select()
        self.sw_tree.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        self.combo_stack = ctk.CTkComboBox(
            self.frame_opts,
            values=["-- Select Stack --"] + sorted(list(cfg.DEFAULT_STACKS.keys())),
            width=200
        )
        self.combo_stack.grid(row=1, column=1, columnspan=2, padx=20, pady=15, sticky="e")

        # --- Section 3: Action Bar ---
        self.btn_process = ctk.CTkButton(
            self,
            text="START PROCESSING",
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#007ACC"
        )
        self.btn_process.grid(row=3, column=0, columnspan=2, sticky="ew", pady=20)

        self.btn_simulate = ctk.CTkButton(
            self,
            text="Simulate (Dry Run)",
            fg_color="transparent",
            border_width=1
        )
        self.btn_simulate.grid(row=4, column=0, columnspan=2, sticky="ew")


# =============================================================================
# Settings (Configuration)
# =============================================================================
class SettingsFrame(ctk.CTkFrame):
    """
    Advanced configuration: Profiles, Filters, Formatting.
    """
    def __init__(self, master: Any, config: Dict[str, Any], profile_names: List[str], **kwargs: Any):
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)
        self.grid_columnconfigure(0, weight=1)

        # 1. Profiles
        self.frame_profiles = ctk.CTkFrame(self)
        self.frame_profiles.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        ctk.CTkLabel(self.frame_profiles, text="Profiles", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.combo_profiles = ctk.CTkComboBox(self.frame_profiles, values=profile_names)
        self.combo_profiles.pack(side="left", padx=10, pady=10, fill="x", expand=True)

        self.btn_load = ctk.CTkButton(self.frame_profiles, text="Load", width=60)
        self.btn_load.pack(side="left", padx=5)
        self.btn_save = ctk.CTkButton(self.frame_profiles, text="Save", width=60)
        self.btn_save.pack(side="left", padx=5)
        self.btn_del = ctk.CTkButton(self.frame_profiles, text="Del", width=60, fg_color="#D9534F", hover_color="#C9302C")
        self.btn_del.pack(side="left", padx=5)

        # 2. Filters
        self.frame_filters = ctk.CTkFrame(self)
        self.frame_filters.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame_filters.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.frame_filters, text="Extensions:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.entry_ext = ctk.CTkEntry(self.frame_filters)
        self.entry_ext.insert(0, ",".join(config.get("extensions", [])))
        self.entry_ext.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_filters, text="Include Regex:").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.entry_inc = ctk.CTkEntry(self.frame_filters)
        self.entry_inc.insert(0, ",".join(config.get("include_patterns", [])))
        self.entry_inc.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self.frame_filters, text="Exclude Regex:").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.entry_exc = ctk.CTkEntry(self.frame_filters)
        self.entry_exc.insert(0, ",".join(config.get("exclude_patterns", [])))
        self.entry_exc.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        self.sw_gitignore = ctk.CTkSwitch(self.frame_filters, text="Respect .gitignore")
        if config.get("respect_gitignore"): self.sw_gitignore.select()
        self.sw_gitignore.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        # 3. Formatting & Security
        self.frame_fmt = ctk.CTkFrame(self)
        self.frame_fmt.grid(row=2, column=0, sticky="ew", pady=(0, 10))

        ctk.CTkLabel(self.frame_fmt, text="Output Strategy", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=5)

        self.sw_individual = ctk.CTkSwitch(self.frame_fmt, text="Create Individual Files")
        if config.get("create_individual_files"): self.sw_individual.select()
        self.sw_individual.pack(anchor="w", padx=10, pady=5)

        self.sw_unified = ctk.CTkSwitch(self.frame_fmt, text="Create Unified Context File")
        if config.get("create_unified_file"): self.sw_unified.select()
        self.sw_unified.pack(anchor="w", padx=10, pady=5)

        ctk.CTkLabel(self.frame_fmt, text="Security & Optimization", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(15, 5))

        self.sw_sanitizer = ctk.CTkSwitch(self.frame_fmt, text="Sanitize Secrets (Redact Keys/IPs)")
        if config.get("enable_sanitizer"): self.sw_sanitizer.select()
        self.sw_sanitizer.pack(anchor="w", padx=10, pady=5)

        self.sw_mask = ctk.CTkSwitch(self.frame_fmt, text="Mask User Paths")
        if config.get("mask_user_paths"): self.sw_mask.select()
        self.sw_mask.pack(anchor="w", padx=10, pady=5)

        self.sw_minify = ctk.CTkSwitch(self.frame_fmt, text="Minify Code (Remove Comments)")
        if config.get("minify_output"): self.sw_minify.select()
        self.sw_minify.pack(anchor="w", padx=10, pady=5)


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

        self.btn_copy = ctk.CTkButton(self, text="Copy Logs", command=self._copy_logs)
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

    if _DND_AVAILABLE:
        app = CtkDnDWrapper()
    else:
        app = ctk.CTk()
        logger.warning("TkinterDnD not available. Drag & Drop disabled.")

    app.title(f"Transcriptor4AI - v{cfg.CURRENT_CONFIG_VERSION}")
    app.geometry("1100x750")

    # Configure Grid Layout (1 Sidebar + 1 Content)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    return app