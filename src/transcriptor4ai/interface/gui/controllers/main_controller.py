from __future__ import annotations

"""
Main Application Controller (GUI Hub).

Acts as the central Mediator and Dependency Container for the graphical 
interface. It coordinates communication between specialized controllers, 
manages the synchronization of application state with visual components, 
and provides access to core logic services.
"""

import logging
import os
import tkinter.messagebox as mb
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk

# Domain Entities & Rules
from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.config_port import IConfigRepository
from transcriptor4ai.domain.ports.model_port import IModelRegistry
from transcriptor4ai.domain.ports.system_port import IFileSystem

# Application Services
from transcriptor4ai.application.services.cost_calculator import CostCalculatorService

# Sub-Controllers
from transcriptor4ai.interface.gui.controllers.execution_controller import ExecutionController
from transcriptor4ai.interface.gui.controllers.feedback_controller import FeedbackController
from transcriptor4ai.interface.gui.controllers.pricing_controller import PricingController
# ProfileController will be refactored to use ports
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController

# UI Utilities
from transcriptor4ai.interface.gui.common import ui_widgets
from transcriptor4ai.interface.gui.common.form_binder import FormBinder
from transcriptor4ai.shared import constants as const
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN APPLICATION CONTROLLER
# ==============================================================================

class AppController:
    """
    Central Hub responsible for orchestrating the GUI lifecycle.
    """

    def __init__(
            self,
            app: ctk.CTk,
            config: Dict[str, Any],
            app_state: Dict[str, Any],
            fs: IFileSystem,
            cache: ICacheRepository,
            config_repo: IConfigRepository,
            registry: IModelRegistry
    ) -> None:
        """
        Initialize the Hub with injected infrastructure implementations.
        """
        # 1. STATE: Initialize session and global data
        self.app = app
        self.config = config
        self.app_state = app_state

        # 2. INFRASTRUCTURE: Assign injected ports
        self._fs = fs
        self._cache = cache
        self._config_repo = config_repo
        self._registry = registry

        # 3. SERVICES: Instantiate application-level logic
        self.binder = FormBinder()
        self.cost_estimator = CostCalculatorService(self._registry)

        # 4. VIEW REFERENCES: Placeholders for lazy registration
        self.dashboard_view: Any = None
        self.settings_view: Any = None
        self.logs_view: Any = None
        self.sidebar_view: Any = None

        # 5. DELEGATION: Initialize specialized controllers
        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)
        self.execution_controller = ExecutionController(self)
        self.pricing_controller = PricingController(self)

    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
        """
        Link visual frame instances to the hub controller.
        """
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    # ==========================================================================
    # INFRASTRUCTURE ACCESSORS (FOR SUB-CONTROLLERS)
    # ==========================================================================

    def get_filesystem(self) -> IFileSystem:
        """Access the injected FileSystem adapter."""
        return self._fs

    def get_cache(self) -> ICacheRepository:
        """Access the injected Cache repository."""
        return self._cache

    def get_config_repo(self) -> IConfigRepository:
        """Access the injected Configuration repository."""
        return self._config_repo

    def get_model_registry(self) -> IModelRegistry:
        """Access the injected Model Registry."""
        return self._registry

    # ==========================================================================
    # CONFIGURATION BINDING & SYNC
    # ==========================================================================

    def sync_view_from_config(self) -> None:
        """
        Populate UI widgets with values from the current configuration dictionary.
        """
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. IO PATHS: Resolve and display absolute paths
        input_path: str = self.config.get("input_path", "")
        output_path: str = self.config.get("output_base_dir", "") or input_path
        self.binder.update_entry(self.dashboard_view.entry_input, input_path)
        self.binder.update_entry(self.dashboard_view.entry_output, output_path)

        # 2. MAPPING: Synchronize switches, checkboxes, and standard entries
        mapping = self.binder.get_ui_mapping(self.dashboard_view, self.settings_view)

        for key, widget in mapping.get("switches", []):
            if key in ["process_modules", "processing_depth"]:
                continue
            self.binder.set_switch_state(self.config, widget, key)

        for key, widget in mapping.get("checkboxes", []):
            self.binder.set_checkbox_state(self.config, widget, key)

        for key, widget in mapping.get("entries", []):
            widget.delete(0, "end")
            widget.insert(0, str(self.config.get(key, "")))

        # 3. STRATEGY: Resolve processing depth and module selection
        depth = self.config.get("processing_depth", "full")
        if depth != "tree_only":
            self.dashboard_view.sw_modules.select()
        else:
            self.dashboard_view.sw_modules.deselect()

        if hasattr(self.dashboard_view, "sw_skeleton"):
            if depth == "skeleton":
                self.dashboard_view.sw_skeleton.select()
            else:
                self.dashboard_view.sw_skeleton.deselect()

        # 4. COLLECTIONS: Format CSV lists for UI entries
        list_fields: List[Tuple[str, ctk.CTkEntry]] = [
            ("extensions", self.settings_view.entry_ext),
            ("include_patterns", self.settings_view.entry_inc),
            ("exclude_patterns", self.settings_view.entry_exc)
        ]
        for key, widget_entry in list_fields:
            widget_entry.delete(0, "end")
            widget_entry.insert(0, ",".join(self.config.get(key, [])))

        # 5. DYNAMIC DATA: Refresh AI Model and Provider lists
        self.on_tree_toggled()
        self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model: str = self.config.get("target_model", const.DEFAULT_MODEL_KEY)
        discovered_models = self._registry.get_available_models()

        providers = sorted(list(set(m["provider"] for m in discovered_models.values())))
        self.settings_view.combo_provider.configure(values=providers)

        # Determine active provider for selection consistency
        model_info = self._registry.get_model_info(target_model)
        current_provider = model_info["provider"] if model_info else (providers[0] if providers else "UNKNOWN")

        self.settings_view.combo_provider.set(current_provider)
        self.pricing_controller.update_model_list(current_provider, preserve_selection=target_model)

        if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
            self.dashboard_view.update_cost_display(0.0)

    def sync_config_from_view(self) -> None:
        """
        Scrape UI widget values into the active configuration dictionary.
        """
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. SCRAPE PATHS: Capture user directory selections
        self.config["input_path"] = self.dashboard_view.entry_input.get().strip()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get().strip()

        # 2. SCRAPE MAPPINGS: Sync boolean and string widgets
        mapping = self.binder.get_ui_mapping(self.dashboard_view, self.settings_view)

        for key, widget in mapping.get("switches", []):
            if key in ["process_modules", "processing_depth"]:
                continue
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("checkboxes", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("entries", []):
            self.config[key] = widget.get().strip()

        # 3. PROCESS DEPTH: Calculate logic strategy based on UI switches
        modules_enabled: bool = bool(self.dashboard_view.sw_modules.get())
        skeleton_enabled: bool = (
                hasattr(self.dashboard_view, "sw_skeleton") and
                bool(self.dashboard_view.sw_skeleton.get())
        )

        # Map UI combinations to domain-level processing depth
        if not modules_enabled:
            self.config["processing_depth"] = "tree_only"
        elif skeleton_enabled:
            self.config["processing_depth"] = "skeleton"
        else:
            self.config["processing_depth"] = "full"

        self.config["process_modules"] = modules_enabled

        # 4. SCRAPE COLLECTIONS: Parse CSV strings into domain lists
        self.config["extensions"] = ui_widgets.parse_list_from_string(self.settings_view.entry_ext.get())
        self.config["include_patterns"] = ui_widgets.parse_list_from_string(self.settings_view.entry_inc.get())
        self.config["exclude_patterns"] = ui_widgets.parse_list_from_string(self.settings_view.entry_exc.get())

        # 5. SCRAPE AI CONTEXT: Capture selected model
        self.config["target_model"] = self.settings_view.combo_model.get()

        # 6. INTEGRITY: Enforce domain-level consistency rules
        domain_cfg.apply_config_integrity(self.config)

    # ==========================================================================
    # DELEGATED ACTION METHODS (FACADE INTERFACE)
    # ==========================================================================

    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """Delegate pipeline execution to the specialized controller."""
        self.execution_controller.run_pipeline(dry_run, overwrite)

    def cancel_processing(self) -> None:
        """Abort the active background execution."""
        self.execution_controller.abort_pipeline()

    def on_pricing_updated(self, data: Optional[Dict[str, Any]]) -> None:
        """Handle completion of the remote pricing discovery task."""
        self.pricing_controller.sync_remote_data(data)

    def on_provider_selected(self, provider: str) -> None:
        """Handle user selection of an AI provider."""
        self.pricing_controller.handle_provider_change(provider)

    def on_model_selected(self, model_name: str) -> None:
        """Handle user selection of a specific LLM."""
        self.pricing_controller.handle_model_change(model_name)

    def load_profile(self) -> None:
        """Delegate configuration profile loading."""
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        """Delegate configuration profile persistence."""
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        """Delegate configuration profile removal."""
        self.profile_controller.delete_profile()

    # ==========================================================================
    # UI EVENT HANDLERS & DIAGNOSTICS
    # ==========================================================================

    def on_stack_selected(self, stack_name: str) -> None:
        """Apply a pre-defined extension stack to the settings view."""
        if stack_name in const.DEFAULT_STACKS:
            extensions = const.DEFAULT_STACKS[stack_name]
            self.settings_view.entry_ext.delete(0, "end")
            self.settings_view.entry_ext.insert(0, ",".join(extensions))
            self.config["extensions"] = extensions

    def on_tree_toggled(self) -> None:
        """Update the visibility of AST controls based on Tree switch state."""
        if self.dashboard_view.sw_tree.get():
            self.dashboard_view.frame_ast.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        else:
            self.dashboard_view.frame_ast.grid_forget()

    def reset_config(self) -> None:
        """Restore all settings to their factory domain defaults."""
        if mb.askyesno(i18n.t("gui.dialogs.confirm_title"), "Reset all settings to defaults?"):
            self.config = domain_cfg.get_default_config(os.getcwd())
            self.sync_view_from_config()
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings reset.")

    def purge_cache(self) -> None:
        """Atomically clear the local processing cache repository."""
        if mb.askyesno("Purge Cache", "Clear the local processing cache?"):
            try:
                self._cache.purge_all()
                mb.showinfo("Cache Cleared", "Local cache has been successfully purged.")
            except Exception as e:
                logger.error(f"UI: Failed to purge cache: {e}")
                mb.showerror("Error", f"Failed to purge cache:\n{e}")