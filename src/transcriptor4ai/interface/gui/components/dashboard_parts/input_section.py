from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame

class InputSection:
    """Handles Source/Dest path selection and file naming configuration."""

    def __init__(
            self,
            master: DashboardFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame.grid_columnconfigure(0, weight=1)

        # --- Source Input ---
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.dashboard.source_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        master.entry_input = ctk.CTkEntry(self.frame, placeholder_text="/path/to/project")
        master.entry_input.insert(0, config.get("input_path", ""))
        master.entry_input.configure(state="readonly")
        master.entry_input.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        master.btn_browse_in = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.buttons.explore"),
            width=80
        )
        master.btn_browse_in.grid(row=1, column=1, padx=10, pady=10)

        # --- Destination Output ---
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.dashboard.dest_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        master.entry_output = ctk.CTkEntry(self.frame, placeholder_text="/path/to/output")
        master.entry_output.insert(0, config.get("output_base_dir", ""))
        master.entry_output.configure(state="readonly")
        master.entry_output.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        master.btn_browse_out = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.buttons.examine"),
            width=80
        )
        master.btn_browse_out.grid(row=3, column=1, padx=10, pady=10)

        # --- Subdir & Prefix ---
        frame_sub = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame_sub.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        master.entry_subdir = ctk.CTkEntry(frame_sub, width=150, placeholder_text="Subdir")
        master.entry_subdir.insert(0, config.get("output_subdir_name", ""))
        master.entry_subdir.pack(side="left", padx=(0, 10))

        master.entry_prefix = ctk.CTkEntry(frame_sub, width=150, placeholder_text="Prefix")
        master.entry_prefix.insert(0, config.get("output_prefix", ""))
        master.entry_prefix.pack(side="left")