from __future__ import annotations

"""
Configuration Synchronization Controller.

Provides bidirectional data binding between the domain configuration model 
(dictionary) and the CustomTkinter UI components. Manages bulk updates 
via FormBinder and handles complex field transformations (CSV parsing).
"""

import os
from typing import List, Tuple, TYPE_CHECKING

import customtkinter as ctk

from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.interface.gui.common import ui_widgets
from transcriptor4ai.interface.gui.common.form_binder import FormBinder
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.coordinator import AppController


# ==============================================================================
# CONFIGURATION SYNCHRONIZER CLASS
# ==============================================================================

class ConfigSynchronizer:
    """
    Delegate responsible for mapping UI state to the session configuration.
    """

    def __init__(self, coordinator: AppController) -> None:
        """
        Initialize with a reference to the main coordinator.
        """
        self.main = coordinator
        self.binder = FormBinder()

    # ==========================================================================
    # PUSH: CONFIG -> VIEW
    # ==========================================================================

    def sync_to_view(self) -> None:
        """
        Populate all UI widgets with values from the current session config.
        """
        # 1. VALIDATION: Ensure views are registered
        if not self.main.dashboard_view or not self.main.settings_view:
            return

        # 2. IO PATHS: Update directory entries
        input_path: str = self.main.config.get("input_path", "")
        output_path: str = self.main.config.get("output_base_dir", "") or input_path
        self.binder.update_entry(self.main.dashboard_view.entry_input, input_path)
        self.binder.update_entry(self.main.dashboard_view.entry_output, output_path)

        # 3. BULK MAPPING: Standard widgets (Switches, Checkboxes, Entries)
        mapping = self.binder.get_ui_mapping(self.main.dashboard_view, self.main.settings_view)

        for key, widget in mapping.get("switches", []):
            if key in ["process_modules", "processing_depth"]:
                continue  # Handled by specialized logic below
            self.binder.set_switch_state(self.main.config, widget, key)

        for key, widget in mapping.get("checkboxes", []):
            self.binder.set_checkbox_state(self.main.config, widget, key)

        for key, widget in mapping.get("entries", []):
            widget.delete(0, "end")
            widget.insert(0, str(self.main.config.get(key, "")))

        # 4. PROCESSING DEPTH: Map enum/logic state to UI switches
        depth = self.main.config.get("processing_depth", "full")

        if depth != "tree_only":
            self.main.dashboard_view.sw_modules.select()
        else:
            self.main.dashboard_view.sw_modules.deselect()

        if hasattr(self.main.dashboard_view, "sw_skeleton"):
            if depth == "skeleton":
                self.main.dashboard_view.sw_skeleton.select()
            else:
                self.main.dashboard_view.sw_skeleton.deselect()

        # 5. COLLECTIONS: Convert lists to CSV strings for entry widgets
        list_fields: List[Tuple[str, ctk.CTkEntry]] = [
            ("extensions", self.main.settings_view.entry_ext),
            ("include_patterns", self.main.settings_view.entry_inc),
            ("exclude_patterns", self.main.settings_view.entry_exc)
        ]
        for key, widget_entry in list_fields:
            widget_entry.delete(0, "end")
            widget_entry.insert(0, ",".join(self.main.config.get(key, [])))

        # 6. DYNAMIC UI & PRICING: Reset dropdowns and refresh model list
        self.main.interactions.on_tree_toggled()
        self.main.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.main.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model: str = self.main.config.get("target_model", const.DEFAULT_MODEL_KEY)
        discovered_models = self.main.get_model_registry().get_available_models()

        providers = sorted(list(set(m["provider"] for m in discovered_models.values())))
        self.main.settings_view.combo_provider.configure(values=providers)

        model_info = self.main.get_model_registry().get_model_info(target_model)
        current_provider = model_info["provider"] if model_info else (providers[0] if providers else "UNKNOWN")

        self.main.settings_view.combo_provider.set(current_provider)
        self.main.pricing_controller.update_model_list(current_provider, preserve_selection=target_model)

        # Reset cost display for new session
        if hasattr(self.main.dashboard_view, "update_cost_display"):
            self.main.dashboard_view.update_cost_display(0.0)

    # ==========================================================================
    # PULL: VIEW -> CONFIG
    # ==========================================================================

    def sync_from_view(self) -> None:
        """
        Scrape all UI widget values and update the active configuration dictionary.
        """
        if not self.main.dashboard_view or not self.main.settings_view:
            return

        # 1. SCRAPE PATHS
        self.main.config["input_path"] = self.main.dashboard_view.entry_input.get().strip()
        self.main.config["output_base_dir"] = self.main.dashboard_view.entry_output.get().strip()

        # 2. BULK SCRAPE: Standard mappings
        mapping = self.binder.get_ui_mapping(self.main.dashboard_view, self.main.settings_view)

        for key, widget in mapping.get("switches", []):
            if key in ["process_modules", "processing_depth"]:
                continue
            self.main.config[key] = bool(widget.get())

        for key, widget in mapping.get("checkboxes", []):
            self.main.config[key] = bool(widget.get())

        for key, widget in mapping.get("entries", []):
            self.main.config[key] = widget.get().strip()

        # 3. DEPTH RESOLUTION: Consolidate multiple switches into 'processing_depth'
        modules_enabled: bool = bool(self.main.dashboard_view.sw_modules.get())
        skeleton_enabled: bool = (
                hasattr(self.main.dashboard_view, "sw_skeleton") and
                bool(self.main.dashboard_view.sw_skeleton.get())
        )

        if not modules_enabled:
            self.main.config["processing_depth"] = "tree_only"
        elif skeleton_enabled:
            self.main.config["processing_depth"] = "skeleton"
        else:
            self.main.config["processing_depth"] = "full"

        self.main.config["process_modules"] = modules_enabled

        # 4. SCRAPE COLLECTIONS: Parse CSV entries into domain-friendly lists
        self.main.config["extensions"] = ui_widgets.parse_list_from_string(
            self.main.settings_view.entry_ext.get()
        )
        self.main.config["include_patterns"] = ui_widgets.parse_list_from_string(
            self.main.settings_view.entry_inc.get()
        )
        self.main.config["exclude_patterns"] = ui_widgets.parse_list_from_string(
            self.main.settings_view.entry_exc.get()
        )

        # 5. SCRAPE AI CONTEXT
        self.main.config["target_model"] = self.main.settings_view.combo_model.get()

        # 6. INTEGRITY: Enforce domain-level consistency rules
        domain_cfg.apply_config_integrity(self.main.config)