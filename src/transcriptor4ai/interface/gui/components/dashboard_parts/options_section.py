from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame


class OptionsSection:
    """Handles Processing Flags (Modules, Tests, Skeleton) and AST visibility."""

    def __init__(
            self,
            master: DashboardFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame.grid_columnconfigure((0, 1, 2), weight=1)

        # --- Main Toggles ---
        master.sw_modules = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.modules"))
        if config.get("process_modules"):
            master.sw_modules.select()
        master.sw_modules.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        master.sw_tests = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.tests"))
        if config.get("process_tests"):
            master.sw_tests.select()
        master.sw_tests.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        master.sw_resources = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.resources"))
        if config.get("process_resources"):
            master.sw_resources.select()
        master.sw_resources.grid(row=0, column=2, padx=20, pady=15, sticky="w")

        # Row 1: Tree & Skeleton
        master.sw_tree = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.gen_tree"))
        if config.get("generate_tree"):
            master.sw_tree.select()
        master.sw_tree.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        master.sw_skeleton = ctk.CTkSwitch(
            self.frame,
            text="Skeleton Mode (AST)",
            command=lambda: self._on_skeleton_toggle(master)
        )
        if config.get("processing_depth") == "skeleton":
            master.sw_skeleton.select()
        master.sw_skeleton.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        # --- AST Details Frame (Hidden by default) ---
        master.frame_ast = ctk.CTkFrame(container, fg_color="transparent")

        master.chk_func = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_func"))
        if config.get("show_functions"):
            master.chk_func.select()
        master.chk_func.pack(side="left", padx=20)

        master.chk_class = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_class"))
        if config.get("show_classes"):
            master.chk_class.select()
        master.chk_class.pack(side="left", padx=20)

        master.chk_meth = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_meth"))
        if config.get("show_methods"):
            master.chk_meth.select()
        master.chk_meth.pack(side="left", padx=20)

    def _on_skeleton_toggle(self, master: DashboardFrame) -> None:
        """Enforce mutual exclusion logic or notify controller via callbacks if needed."""
        # Simple visual logic could go here, but main logic is in controller.
        pass