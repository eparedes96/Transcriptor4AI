from __future__ import annotations

"""
Input Selection UI Section.

Constructs the visual component for project path selection and output 
configuration. Handles the registration of directory picker entries 
and naming parameters within the main Dashboard container.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to prevent circular dependency with the parent Frame
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW COMPONENT: INPUT SECTION
# ==============================================================================

class InputSection:
    """
    Sub-view component for the Dashboard handling Source/Dest path logic.

    Attributes are registered directly on the DashboardFrame to enable
    automatic data binding via the FormBinder utility.
    """

    def __init__(
            self,
            master: DashboardFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the input selection layout.

        Args:
            master: The parent DashboardFrame instance for widget registration.
            container: The visual layout container (Scrollable Frame).
            config: Initial configuration state for value population.
        """
        # 1. SETUP: Create main section container
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.frame.grid_columnconfigure(0, weight=1)

        # ======================================================================
        # SOURCE CONFIGURATION
        # ======================================================================

        # 2. LABEL: Section identification for source project
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.dashboard.source_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=0, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # 3. INPUT: Project path display (Read-only to force picker usage)
        master.entry_input = ctk.CTkEntry(self.frame, placeholder_text="/path/to/project")
        master.entry_input.insert(0, config.get("input_path", ""))
        master.entry_input.configure(state="readonly")
        master.entry_input.grid(row=1, column=0, padx=10, pady=10, sticky="ew")

        # 4. ACTION: Project directory picker trigger
        master.btn_browse_in = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.buttons.explore"),
            width=80
        )
        master.btn_browse_in.grid(row=1, column=1, padx=10, pady=10)

        # ======================================================================
        # DESTINATION CONFIGURATION
        # ======================================================================

        # 5. LABEL: Section identification for output artifacts
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.dashboard.dest_header"),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("gray40", "gray60")
        ).grid(row=2, column=0, columnspan=2, padx=10, pady=(10, 0), sticky="w")

        # 6. INPUT: Output base path display
        master.entry_output = ctk.CTkEntry(self.frame, placeholder_text="/path/to/output")
        master.entry_output.insert(0, config.get("output_base_dir", ""))
        master.entry_output.configure(state="readonly")
        master.entry_output.grid(row=3, column=0, padx=10, pady=10, sticky="ew")

        # 7. ACTION: Output directory picker trigger
        master.btn_browse_out = ctk.CTkButton(
            self.frame,
            text=i18n.t("gui.buttons.examine"),
            width=80
        )
        master.btn_browse_out.grid(row=3, column=1, padx=10, pady=10)

        # ======================================================================
        # ARTIFACT NAMING (SUBDIR & PREFIX)
        # ======================================================================

        # 8. LAYOUT: Horizontal frame for naming options
        frame_sub = ctk.CTkFrame(self.frame, fg_color="transparent")
        frame_sub.grid(row=5, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        # 9. INPUT: Target subdirectory name
        master.entry_subdir = ctk.CTkEntry(frame_sub, width=150, placeholder_text="Subdir")
        master.entry_subdir.insert(0, config.get("output_subdir_name", ""))
        master.entry_subdir.pack(side="left", padx=(0, 10))

        # 10. INPUT: Filename prefix for consolidated files
        master.entry_prefix = ctk.CTkEntry(frame_sub, width=150, placeholder_text="Prefix")
        master.entry_prefix.insert(0, config.get("output_prefix", ""))
        master.entry_prefix.pack(side="left")

        logger.debug("UI: InputSelection component initialized and registered.")