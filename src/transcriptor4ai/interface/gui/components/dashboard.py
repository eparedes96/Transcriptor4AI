from __future__ import annotations

"""
Dashboard UI Component.

Constructs the primary workspace for the application. Manages input/output
path selection, processing mode toggles (modules, tests, resources),
and execution triggers. Implements a scrollable layout to ensure
usability across different window dimensions.
"""

from typing import Any, Dict

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

# ==============================================================================
# DASHBOARD VIEW COMPONENT
# ==============================================================================

class DashboardFrame(ctk.CTkFrame):
    """
    Main execution dashboard for Transcriptor4AI.

    Provides an interactive interface for filesystem path resolution and
    core transcription parameters. Encapsulated within a scrollable frame
    to handle complex widget hierarchies.
    """

    def __init__(self, master: Any, config: Dict[str, Any], **kwargs: Any):
        """
        Initialize the dashboard with persistent session configuration.

        Args:
            master: Parent container or window.
            config: Initial configuration state for widget population.
        """
        super().__init__(master, corner_radius=10, fg_color="transparent", **kwargs)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. MAIN SCROLLABLE CONTAINER ---
        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.grid(row=0, column=0, sticky="nsew")
        self.scroll.grid_columnconfigure(0, weight=1)

        # --- 2. SECTION: I/O PATH MANAGEMENT ---
        self.frame_io = ctk.CTkFrame(self.scroll)
        self.frame_io.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame_io.grid_columnconfigure(0, weight=1)

        # Source Path Header
        ctk.CTkLabel(
            self.frame_io,
            text=i18n.t("gui.dashboard.source_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # Source Input Field
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

        # Destination Path Header
        ctk.CTkLabel(
            self.frame_io,
            text=i18n.t("gui.dashboard.dest_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # Destination Input Field
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

        # --- 3. SECTION: ARTIFACT NAMING (SUBDIR & PREFIX) ---
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

        self.frame_sub = ctk.CTkFrame(self.frame_io, fg_color="transparent")
        self.frame_sub.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        self.entry_subdir = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Subdir")
        self.entry_subdir.insert(0, config.get("output_subdir_name", ""))
        self.entry_subdir.pack(side="left", padx=(0, 10))

        self.entry_prefix = ctk.CTkEntry(self.frame_sub, width=150, placeholder_text="Prefix")
        self.entry_prefix.insert(0, config.get("output_prefix", ""))
        self.entry_prefix.pack(side="left")

        # --- 4. SECTION: CONTENT PROCESSING TOGGLES ---
        self.frame_opts = ctk.CTkFrame(self.scroll)
        self.frame_opts.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame_opts.grid_columnconfigure((0, 1, 2), weight=1)

        # Modules Toggle
        self.sw_modules = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.modules"))
        if config.get("process_modules"):
            self.sw_modules.select()
        self.sw_modules.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        # Tests Toggle
        self.sw_tests = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.tests"))
        if config.get("process_tests"):
            self.sw_tests.select()
        self.sw_tests.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # Resources Toggle
        self.sw_resources = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.resources"))
        if config.get("process_resources"):
            self.sw_resources.select()
        self.sw_resources.grid(row=0, column=2, padx=20, pady=15, sticky="w")

        # Tree Generation Toggle
        self.sw_tree = ctk.CTkSwitch(self.frame_opts, text=i18n.t("gui.checkboxes.gen_tree"))
        if config.get("generate_tree"):
            self.sw_tree.select()
        self.sw_tree.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        # --- 5. SECTION: STATIC ANALYSIS (AST) PARAMETERS ---
        self.frame_ast = ctk.CTkFrame(self.scroll, fg_color="transparent")

        # Function signatures
        self.chk_func = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_func"))
        if config.get("show_functions"):
            self.chk_func.select()
        self.chk_func.pack(side="left", padx=20)

        # Class hierarchies
        self.chk_class = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_class"))
        if config.get("show_classes"):
            self.chk_class.select()
        self.chk_class.pack(side="left", padx=20)

        # Method details
        self.chk_meth = ctk.CTkCheckBox(self.frame_ast, text=i18n.t("gui.dashboard.ast_meth"))
        if config.get("show_methods"):
            self.chk_meth.select()
        self.chk_meth.pack(side="left", padx=20)

        # --- 6. SECTION: PIPELINE EXECUTION TRIGGERS ---
        self.btn_process = ctk.CTkButton(
            self.scroll,
            text=i18n.t("gui.dashboard.btn_start"),
            height=50,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color="#1f538d"
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