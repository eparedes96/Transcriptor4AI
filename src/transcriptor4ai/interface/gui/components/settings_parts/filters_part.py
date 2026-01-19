from __future__ import annotations

"""
UI Section for File Filtering.

Handles the visual layout and widget registration for extension whitelists, 
regex-based inclusion/exclusion patterns, and gitignore compliance logic.
"""

from typing import TYPE_CHECKING, Any, Dict

import customtkinter as ctk

from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.components.settings import SettingsFrame


class FiltersSection:
    """
    Handles the UI for extension whitelists, regex patterns, and gitignore logic.
    """

    def __init__(
            self,
            master: SettingsFrame,
            container: ctk.CTkScrollableFrame,
            config: Dict[str, Any]
    ) -> None:
        """
        Initialize the filters section and register widgets in the master.

        Args:
            master: The parent SettingsFrame for widget registration.
            container: The scrollable frame for layout placement.
            config: Active session state for initial values.
        """
        frame = ctk.CTkFrame(container)
        frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        frame.grid_columnconfigure(1, weight=1)

        # Row 0: Extensions (CSV)
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.labels.extensions")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")

        master.entry_ext = ctk.CTkEntry(frame)
        master.entry_ext.insert(0, ",".join(config.get("extensions", [])))
        master.entry_ext.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        # Row 1: Include Regex
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.labels.include")
        ).grid(row=1, column=0, padx=10, pady=10, sticky="w")

        master.entry_inc = ctk.CTkEntry(frame)
        master.entry_inc.insert(0, ",".join(config.get("include_patterns", [])))
        master.entry_inc.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

        # Row 2: Exclude Regex
        ctk.CTkLabel(
            frame,
            text=i18n.t("gui.labels.exclude")
        ).grid(row=2, column=0, padx=10, pady=10, sticky="w")

        master.entry_exc = ctk.CTkEntry(frame)
        master.entry_exc.insert(0, ",".join(config.get("exclude_patterns", [])))
        master.entry_exc.grid(row=2, column=1, padx=10, pady=10, sticky="ew")

        # Row 3: Gitignore Compliance Toggle
        master.sw_gitignore = ctk.CTkSwitch(
            frame,
            text=i18n.t("gui.checkboxes.gitignore")
        )
        if config.get("respect_gitignore"):
            master.sw_gitignore.select()
        master.sw_gitignore.grid(row=3, column=0, columnspan=2, padx=10, pady=10, sticky="w")