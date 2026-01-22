from __future__ import annotations

"""
Main Application Controller.

Acts as the Orchestrator (Hub).
It initializes the core services and delegates specialized logic to
ExecutionController and PricingController.
"""

import logging
import os
import tkinter.messagebox as mb
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk

from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.estimator import CostEstimator
from transcriptor4ai.core.services.registry import ModelRegistry
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.domain import constants as const
from transcriptor4ai.interface.gui.controllers.execution_controller import ExecutionController
from transcriptor4ai.interface.gui.controllers.feedback_controller import FeedbackController
from transcriptor4ai.interface.gui.controllers.pricing_controller import PricingController
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController
from transcriptor4ai.interface.gui.utils import tk_helpers
from transcriptor4ai.interface.gui.utils.binder import FormBinder
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


class AppController:
    """
    Central Hub Controller.
    Holds the state (config, app_state) and references to Views and Core Services.
    """

    def __init__(
            self,
            app: ctk.CTk,
            config: Dict[str, Any],
            app_state: Dict[str, Any]
    ):
        self.app = app
        self.config = config
        self.app_state = app_state

        # View References (Set via register_views)
        self.dashboard_view: Any = None
        self.settings_view: Any = None
        self.logs_view: Any = None
        self.sidebar_view: Any = None

        # Core Services
        self.binder = FormBinder()
        self.registry = ModelRegistry()
        self.cost_estimator = CostEstimator(self.registry)
        self.cache_service = CacheService()

        # Sub-Controllers (Delegation)
        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)
        self.execution_controller = ExecutionController(self)
        self.pricing_controller = PricingController(self)

    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
        """Link visual frame instances to the controller."""
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    # -------------------------------------------------------------------------
    # CONFIGURATION BINDING (Kept in Main as it touches all views)
    # -------------------------------------------------------------------------

    def sync_view_from_config(self) -> None:
        """Populate UI widgets with values from configuration."""
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. IO Paths
        input_path: str = self.config.get("input_path", "")
        output_path: str = self.config.get("output_base_dir", "") or input_path
        self.binder.update_entry(self.dashboard_view.entry_input, input_path)
        self.binder.update_entry(self.dashboard_view.entry_output, output_path)

        # 2. Generic Mapping
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

        # 3. Processing Depth
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

        # 4. CSV Lists
        list_fields: List[Tuple[str, ctk.CTkEntry]] = [
            ("extensions", self.settings_view.entry_ext),
            ("include_patterns", self.settings_view.entry_inc),
            ("exclude_patterns", self.settings_view.entry_exc)
        ]
        for key, widget_entry in list_fields:
            widget_entry.delete(0, "end")
            widget_entry.insert(0, ",".join(self.config.get(key, [])))

        # 5. Dynamic Data
        self.on_tree_toggled()
        self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model: str = self.config.get("target_model", const.DEFAULT_MODEL_KEY)
        discovered_models = self.registry.get_available_models()
        providers = sorted(list(set(m["provider"] for m in discovered_models.values())))
        self.settings_view.combo_provider.configure(values=providers)

        current_provider: str = "UNKNOWN"
        model_info = self.registry.get_model_info(target_model)
        if model_info:
            current_provider = model_info["provider"]
        elif providers:
            current_provider = providers[0]

        self.settings_view.combo_provider.set(current_provider)
        # Delegate filtering to pricing controller to keep UI in sync
        self.pricing_controller.update_model_list(current_provider, preserve_selection=target_model)

        if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
            self.dashboard_view.update_cost_display(0.0)

    def sync_config_from_view(self) -> None:
        """Scrape UI widget values into configuration."""
        if not self.dashboard_view or not self.settings_view:
            return

        self.config["input_path"] = self.dashboard_view.entry_input.get().strip()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get().strip()

        mapping = self.binder.get_ui_mapping(self.dashboard_view, self.settings_view)
        for key, widget in mapping.get("switches", []):
            if key in ["process_modules", "processing_depth"]:
                continue
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("checkboxes", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("entries", []):
            self.config[key] = widget.get().strip()

        modules_enabled: bool = bool(self.dashboard_view.sw_modules.get())
        skeleton_enabled: bool = (
                hasattr(self.dashboard_view, "sw_skeleton") and
                bool(self.dashboard_view.sw_skeleton.get())
        )

        if not modules_enabled:
            self.config["processing_depth"] = "tree_only"
        elif skeleton_enabled:
            self.config["processing_depth"] = "skeleton"
        else:
            self.config["processing_depth"] = "full"

        self.config["process_modules"] = modules_enabled

        self.config["extensions"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_ext.get()
        )
        self.config["include_patterns"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_inc.get()
        )
        self.config["exclude_patterns"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_exc.get()
        )
        self.config["target_model"] = self.settings_view.combo_model.get()

    # -------------------------------------------------------------------------
    # DELEGATED METHODS (The Facade)
    # -------------------------------------------------------------------------

    # Execution
    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        self.execution_controller.run_pipeline(dry_run, overwrite)

    def cancel_processing(self) -> None:
        self.execution_controller.abort_pipeline()

    # Note: _on_process_complete and _handle_process_result are strictly internal
    # to ExecutionController now, accessed via callbacks.

    def _toggle_ui(self, disabled: bool) -> None:
        self.execution_controller.set_ui_state(disabled)

    # Pricing & Models
    def on_pricing_updated(self, data: Optional[Dict[str, Any]]) -> None:
        self.pricing_controller.sync_remote_data(data)

    def on_provider_selected(self, provider: str) -> None:
        self.pricing_controller.handle_provider_change(provider)

    def _filter_models_by_provider(self, provider: str, preserve_selection: Optional[str] = None) -> None:
        self.pricing_controller.update_model_list(provider, preserve_selection)

    def on_model_selected(self, model_name: str) -> None:
        self.pricing_controller.handle_model_change(model_name)

    # Profiles
    def load_profile(self) -> None:
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        self.profile_controller.delete_profile()

    # Feedback
    def request_feedback(self) -> None:
        self.feedback_controller.on_feedback_requested()

    # Local UI Events
    def on_stack_selected(self, stack_name: str) -> None:
        if stack_name in const.DEFAULT_STACKS:
            extensions = const.DEFAULT_STACKS[stack_name]
            self.settings_view.entry_ext.delete(0, "end")
            self.settings_view.entry_ext.insert(0, ",".join(extensions))
            self.config["extensions"] = extensions

    def on_tree_toggled(self) -> None:
        if self.dashboard_view.sw_tree.get():
            self.dashboard_view.frame_ast.grid(
                row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10)
            )
        else:
            self.dashboard_view.frame_ast.grid_forget()

    def on_skeleton_toggled(self) -> None:
        self.sync_config_from_view()
        logger.debug(f"Skeleton Mode updated: {self.config['processing_depth']}")

    def reset_config(self) -> None:
        if mb.askyesno(i18n.t("gui.dialogs.confirm_title"), "Reset all settings to defaults?"):
            self.config = cfg.get_default_config()
            self.sync_view_from_config()
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings reset.")

    def purge_cache(self) -> None:
        if mb.askyesno("Purge Cache", "Clear the local processing cache?"):
            try:
                self.cache_service.purge_all()
                mb.showinfo("Cache Cleared", "Local cache has been successfully purged.")
            except Exception as e:
                logger.error(f"Failed to purge cache: {e}")
                mb.showerror("Error", f"Failed to purge cache:\n{e}")