from __future__ import annotations

"""
UI Form Binding Utility.

Provides a declarative mapping and synchronization layer between the 
application configuration dictionary and CustomTkinter widgets. 
Encapsulates low-level widget manipulation to maintain controller cleanliness.
"""

from typing import Any, Dict, List, Tuple

import customtkinter as ctk


class FormBinder:
    """
    Orchestrates the bidirectional data flow between UI components and config.
    """

    @staticmethod
    def get_ui_mapping(dashboard: Any, settings: Any) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Define the declarative relationship between config keys and UI widgets.

        Args:
            dashboard: The Dashboard view instance.
            settings: The Settings view instance.

        Returns:
            Dict: Grouped mappings by widget type.
        """
        if not dashboard or not settings:
            return {}

        return {
            "switches": [
                ("process_modules", dashboard.sw_modules),
                ("process_tests", dashboard.sw_tests),
                ("process_resources", dashboard.sw_resources),
                ("generate_tree", dashboard.sw_tree),
                ("respect_gitignore", settings.sw_gitignore),
                ("create_individual_files", settings.sw_individual),
                ("create_unified_file", settings.sw_unified),
                ("enable_sanitizer", settings.sw_sanitizer),
                ("mask_user_paths", settings.sw_mask),
                ("minify_output", settings.sw_minify),
                ("save_error_log", settings.sw_error_log),
            ],
            "checkboxes": [
                ("show_functions", dashboard.chk_func),
                ("show_classes", dashboard.chk_class),
                ("show_methods", dashboard.chk_meth),
            ],
            "entries": [
                ("output_subdir_name", dashboard.entry_subdir),
                ("output_prefix", dashboard.entry_prefix),
            ]
        }

    def update_entry(self, entry: ctk.CTkEntry, text: str) -> None:
        """
        Update a CTkEntry's content while bypassing readonly constraints.

        Args:
            entry: Target entry widget.
            text: New text to insert.
        """
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="readonly")

    def set_switch_state(self, config: Dict[str, Any], switch: ctk.CTkSwitch, key: str) -> None:
        """Set a CTkSwitch state based on config boolean value."""
        if config.get(key):
            switch.select()
        else:
            switch.deselect()

    def set_checkbox_state(self, config: Dict[str, Any], chk: ctk.CTkCheckBox, key: str) -> None:
        """Set a CTkCheckBox state based on config boolean value."""
        if config.get(key):
            chk.select()
        else:
            chk.deselect()