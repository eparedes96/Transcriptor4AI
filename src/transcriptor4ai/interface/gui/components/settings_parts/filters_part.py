from __future__ import annotations

"""
File Filtering UI Section.

Constructs the visual component for defining project scope through extension 
whitelists, regex-based inclusion/exclusion patterns, and .gitignore 
compliance toggles. Integrates directly into the Settings layout.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.shared.i18n import i18n

# Use TYPE_CHECKING to prevent circular imports with the Settings view
if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# VIEW COMPONENT: FILTERS SECTION
# ==============================================================================

class FiltersSection:
    """
    Sub-view component for the SettingsFrame handling file discovery rules.

    Attributes are registered directly on the master (SettingsFrame) to allow
    declarative synchronization via the FormBinder.
    """

    def __init__(
        self,
        master: SettingsFrame,
        container: ctk.CTkScrollableFrame,
        config: Dict[str, Any]
    ) -> None:
        """
        Initialize the filters layout and populate initial values.

        Args:
            master: The parent SettingsFrame instance for widget registration.
            container: The scrollable layout manager for placement.
            config: Initial configuration state for value population.
        """
        # 1. SETUP: Create the section container with weight on the input column
        self.frame = ctk.CTkFrame(container)
        self.frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.frame.grid_columnconfigure(1, weight=1)

        # ======================================================================
        # EXTENSION WHITELIST
        # ======================================================================

        # 2. LABEL: Identification for the extension CSV field
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.labels.extensions")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        # 3. INPUT: Comma-separated list of allowed extensions
        master.entry_ext = ctk.CTkEntry(self.frame)
        master.entry_ext.insert(0, ",".join(config.get("extensions", [])))
        master.entry_ext.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # ======================================================================
        # REGEX PATTERNS (INCLUDE/EXCLUDE)
        # ======================================================================

        # 4. ROW: Inclusion Regex Pattern
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.labels.include")
        ).grid(row=1, column=0, padx=10, pady=10, sticky="w")

        master.entry_inc = ctk.CTkEntry(self.frame)
        master.entry_inc.insert(0, ",".join(config.get("include_patterns", [])))
        master.entry_inc.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # 5. ROW: Exclusion Regex Pattern
        ctk.CTkLabel(
            self.frame,
            text=i18n.t("gui.labels.exclude")
        ).grid(row=2, column=0, padx=10, pady=10, sticky="w")

        master.entry_exc = ctk.CTkEntry(self.frame)
        master.entry_exc.insert(0, ",".join(config.get("exclude_patterns", [])))
        master.entry_exc.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        # ======================================================================
        # COMPLIANCE TOGGLES
        # ======================================================================

        # 6. SWITCH: Native .gitignore rule ingestion
        master.sw_gitignore = ctk.CTkSwitch(
            self.frame,
            text=i18n.t("gui.checkboxes.gitignore")
        )
        if config.get("respect_gitignore"):
            master.sw_gitignore.select()
        master.sw_gitignore.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")

        logger.debug("UI: FiltersSection successfully initialized and registered.")