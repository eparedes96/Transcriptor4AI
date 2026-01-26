from __future__ import annotations

"""
Transcription Options UI Section.

Constructs the visual controls for processing scope and depth. Manages switches 
for module/test/resource selection and configures the 'Skeleton Mode' strategy 
along with its associated static analysis (AST) metadata checkboxes.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to prevent circular imports with the parent view
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW COMPONENT: OPTIONS SECTION
# ==============================================================================

class OptionsSection:
    """
    Sub-view component for the Dashboard handling content flags and strategies.

    Attributes are registered directly on the DashboardFrame to support
    automated configuration binding via the FormBinder.
    """

    def __init__(
            self,
            master: DashboardFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the options layout and bind initial states.

        Args:
            master: The parent DashboardFrame instance for widget registration.
            container: The visual layout manager (Scrollable Frame).
            config: Initial configuration state for value population.
        """
        # 1. SETUP: Create section container with responsive grid
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        self.frame.grid_columnconfigure((0, 1, 2), weight=1)

        # ======================================================================
        # CONTENT SCOPE TOGGLES
        # ======================================================================

        # 2. SWITCH: Core logic modules (Source Code)
        master.sw_modules = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.modules"))
        if config.get("process_modules"):
            master.sw_modules.select()
        master.sw_modules.grid(row=0, column=0, padx=20, pady=15, sticky="w")

        # 3. SWITCH: Test suites and unit tests
        master.sw_tests = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.tests"))
        if config.get("process_tests"):
            master.sw_tests.select()
        master.sw_tests.grid(row=0, column=1, padx=20, pady=15, sticky="w")

        # 4. SWITCH: Non-code project resources (Docs/Config)
        master.sw_resources = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.resources"))
        if config.get("process_resources"):
            master.sw_resources.select()
        master.sw_resources.grid(row=0, column=2, padx=20, pady=15, sticky="w")

        # ======================================================================
        # TRANSCRIPTION STRATEGY TOGGLES
        # ======================================================================

        # 5. SWITCH: Directory tree generation toggle
        master.sw_tree = ctk.CTkSwitch(self.frame, text=i18n.t("gui.checkboxes.gen_tree"))
        if config.get("generate_tree"):
            master.sw_tree.select()
        master.sw_tree.grid(row=1, column=0, padx=20, pady=15, sticky="w")

        # 6. SWITCH: Skeleton Mode (AST-based body stripping)
        # Includes a command callback to allow real-time UI reactions
        master.sw_skeleton = ctk.CTkSwitch(
            self.frame,
            text="Skeleton Mode (AST)",
            command=lambda: self._on_skeleton_toggle(master)
        )
        if config.get("processing_depth") == "skeleton":
            master.sw_skeleton.select()
        master.sw_skeleton.grid(row=1, column=1, padx=20, pady=15, sticky="w")

        # ======================================================================
        # STATIC ANALYSIS (AST) CONFIGURATION
        # ======================================================================

        # 7. LAYOUT: Frame for detailed symbol visibility (mapped to tree output)
        # This frame is typically toggled based on the sw_tree state
        master.frame_ast = ctk.CTkFrame(container, fg_color="transparent")

        # 8. CHECKBOX: Function signatures in tree
        master.chk_func = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_func"))
        if config.get("show_functions"):
            master.chk_func.select()
        master.chk_func.pack(side="left", padx=20)

        # 9. CHECKBOX: Class definitions in tree
        master.chk_class = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_class"))
        if config.get("show_classes"):
            master.chk_class.select()
        master.chk_class.pack(side="left", padx=20)

        # 10. CHECKBOX: Method visibility inside classes
        master.chk_meth = ctk.CTkCheckBox(master.frame_ast, text=i18n.t("gui.dashboard.ast_meth"))
        if config.get("show_methods"):
            master.chk_meth.select()
        master.chk_meth.pack(side="left", padx=20)

        logger.debug("UI: OptionsSection successfully initialized and registered.")

    # ==========================================================================
    # INTERNAL EVENT HANDLING
    # ==========================================================================

    def _on_skeleton_toggle(self, master: DashboardFrame) -> None:
        """
        Handle UI state changes when Skeleton Mode is toggled.

        Currently acts as a hook for the controller to sync state.
        Detailed business logic (mutual exclusions) is handled at the
        controller level.
        """
        # Notify of UI interaction for potential reactive changes
        logger.debug("UI: Skeleton Mode toggle interaction detected.")