from __future__ import annotations

"""
Main Application Controller.

Bridges the View (UI Components) and the Model (Core Logic). 
Handles user interactions, configuration sync, and process execution. 
Acts as a Facade for specialized sub-controllers (Profiles, Feedback), 
managing the asynchronous lifecycle of the transcription pipeline. 
Integrates ModelRegistry for dynamic discovery and context window validation 
without intrusive API key interruptions.
"""

import logging
import os
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk

from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.estimator import CostEstimator
from transcriptor4ai.core.services.registry import ModelRegistry
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.domain import constants as const
from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.interface.gui.controllers.feedback_controller import (
    FeedbackController,
)
from transcriptor4ai.interface.gui.controllers.profile_controller import (
    ProfileController,
)
from transcriptor4ai.interface.gui.dialogs import crash_modal, results_modal
from transcriptor4ai.interface.gui.utils import tk_helpers
from transcriptor4ai.interface.gui.utils.binder import FormBinder
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


class AppController:
    """
    Central controller class that bridges the UI (View) and the Core (Model).

    It manages the application state, configuration syncing via dynamic
    discovery, and thread-safe event handling for long-running tasks.
    """

    def __init__(
            self,
            app: ctk.CTk,
            config: Dict[str, Any],
            app_state: Dict[str, Any]
    ):
        """
        Initialize the controller with application context and state.

        Args:
            app: Root CustomTkinter application instance.
            config: Active session configuration dictionary.
            app_state: Global persistent application state.
        """
        self.app = app
        self.config = config
        self.app_state = app_state
        self._cancellation_event = threading.Event()

        # Shortcuts to registered View components
        self.dashboard_view: Any = None
        self.settings_view: Any = None
        self.logs_view: Any = None
        self.sidebar_view: Any = None

        # Core Services
        self.binder = FormBinder()
        self.registry = ModelRegistry()
        self.cost_estimator = CostEstimator(self.registry)
        self.cache_service = CacheService()

        # Initialize Sub-Controllers (Delegation Pattern)
        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)

    # -------------------------------------------------------------------------
    # VIEW REGISTRATION
    # -------------------------------------------------------------------------

    def register_views(
            self,
            dashboard: Any,
            settings: Any,
            logs: Any,
            sidebar: Any
    ) -> None:
        """
        Link visual frame instances to the controller.

        Args:
            dashboard: Dashboard logic and IO frame.
            settings: Advanced configuration frame.
            logs: Real-time logging console frame.
            sidebar: Primary navigation frame.
        """
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    # -------------------------------------------------------------------------
    # CONFIGURATION SYNCHRONIZATION
    # -------------------------------------------------------------------------

    def sync_view_from_config(self) -> None:
        """
        Populate UI widgets with values from the internal configuration state.

        Resolves dynamic provider/model lists from the Registry.
        """
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. IO Paths
        input_path: str = self.config.get("input_path", "")
        output_path: str = self.config.get("output_base_dir", "") or input_path
        self.binder.update_entry(self.dashboard_view.entry_input, input_path)
        self.binder.update_entry(self.dashboard_view.entry_output, output_path)

        # 2. Generic Declarative Mapping
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

        # 3. Processing Depth Mapping
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

        # 4. List Fields (CSV Transformation)
        list_fields: List[Tuple[str, ctk.CTkEntry]] = [
            ("extensions", self.settings_view.entry_ext),
            ("include_patterns", self.settings_view.entry_inc),
            ("exclude_patterns", self.settings_view.entry_exc)
        ]
        for key, widget_entry in list_fields:
            widget_entry.delete(0, "end")
            widget_entry.insert(0, ",".join(self.config.get(key, [])))

        # 5. Dynamic Model Discovery
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
        self._filter_models_by_provider(current_provider, preserve_selection=target_model)

        if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
            self.dashboard_view.update_cost_display(0.0)

    def sync_config_from_view(self) -> None:
        """Scrape UI widget values into the internal configuration state."""
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

        # Depth Resolution
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

        # Ruff E501: Wrapped CSV parsing calls
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
    # CORE PIPELINE EXECUTION
    # -------------------------------------------------------------------------

    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """Initiate the transcription pipeline in a background thread."""
        self.sync_config_from_view()

        input_path: str = self.config.get("input_path", "")
        if not os.path.isdir(input_path):
            mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.dialogs.invalid_input"))
            return

        self._toggle_ui(disabled=True)
        btn_text: str = i18n.t("gui.dashboard.btn_simulating") if dry_run else "PROCESSING..."
        self.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        self._cancellation_event.clear()
        logger.debug(f"Starting pipeline (DryRun={dry_run}). Config: {self.config}")

        threading.Thread(
            target=threads.run_pipeline_task,
            args=(
                self.config,
                overwrite,
                dry_run,
                self._on_process_complete,
                self._cancellation_event
            ),
            daemon=True
        ).start()

    def cancel_processing(self) -> None:
        """Signal the background pipeline to abort execution."""
        if not self._cancellation_event.is_set():
            logger.info("User requested task cancellation. Signaling workers...")
            self._cancellation_event.set()
            self.dashboard_view.btn_process.configure(text="CANCELING...", state="disabled")

    def _on_process_complete(self, result: Any) -> None:
        """Handle pipeline completion from the background thread."""
        self.app.after(0, lambda: self._handle_process_result(result))

    def _handle_process_result(self, result: Any) -> None:
        """Process pipeline result, managing collisions and context validation."""
        if isinstance(result, PipelineResult) and not result.ok:
            if result.existing_files:
                msg_files = "\n".join(result.existing_files)
                msg = i18n.t("gui.popups.overwrite_msg", files=msg_files)
                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    self.start_processing(dry_run=False, overwrite=True)
                    return

        self._toggle_ui(disabled=False)
        self.dashboard_view.btn_process.configure(
            text=i18n.t("gui.dashboard.btn_start"),
            fg_color="#1F6AA5"
        )

        if isinstance(result, PipelineResult):
            if result.ok:
                target_model: str = self.config.get("target_model", const.DEFAULT_MODEL_KEY)

                # Financial Calculation
                cost: float = self.cost_estimator.calculate_cost(result.token_count, target_model)
                if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
                    self.dashboard_view.update_cost_display(cost)

                # Context Window Validation
                limit: int = self.cost_estimator.get_context_limit(target_model)
                if result.token_count > limit:
                    warning_msg: str = (
                        f"Warning: Estimated tokens ({result.token_count:,}) exceed "
                        f"the model's context window ({limit:,}).\n\n"
                        "The output will likely be truncated by the AI provider."
                    )
                    mb.showwarning("Context Overflow", warning_msg)

                results_modal.show_results_window(self.app, result)
            else:
                err_msg: str = result.error.lower() if result.error else ""
                if self._cancellation_event.is_set() and "cancelled" in err_msg:
                    logger.info("Pipeline stopped by user signal.")
                else:
                    mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)
        elif isinstance(result, Exception):
            crash_modal.show_crash_modal(str(result), "See logs for details.", self.app)

    def _toggle_ui(self, disabled: bool) -> None:
        """Helper to enable/disable interaction during processing."""
        state: str = "disabled" if disabled else "normal"
        self.dashboard_view.btn_process.configure(state=state)
        self.dashboard_view.btn_simulate.configure(state=state)

    # -------------------------------------------------------------------------
    # DYNAMIC DISCOVERY & UI UPDATES
    # -------------------------------------------------------------------------

    def on_pricing_updated(self, data: Optional[Dict[str, Any]]) -> None:
        """Handle remote discovery completion and refresh UI components."""
        self.cost_estimator.update_live_pricing()

        if self.dashboard_view and hasattr(self.dashboard_view, "set_pricing_status"):
            is_live: bool = self.registry._is_live_synced
            self.dashboard_view.set_pricing_status(is_live=is_live)

        self.sync_view_from_config()
        logger.info("UI: Model and pricing discovery synced and views refreshed.")

    def on_provider_selected(self, provider: str) -> None:
        """Update the model selection list when the provider changes."""
        self._filter_models_by_provider(provider)
        new_model: str = self.settings_view.combo_model.get()
        self.config["target_model"] = new_model
        self.on_model_selected(new_model)

    def _filter_models_by_provider(
            self,
            provider: str,
            preserve_selection: Optional[str] = None
    ) -> None:
        """Filter the model list based on discovered data."""
        discovered = self.registry.get_available_models()
        models = sorted([
            m_id for m_id, info in discovered.items()
            if info.get("provider") == provider
        ])

        if not models:
            models = ["-- No Models --"]

        self.settings_view.combo_model.configure(values=models)

        if preserve_selection and preserve_selection in models:
            self.settings_view.combo_model.set(preserve_selection)
        else:
            self.settings_view.combo_model.set(models[0])
            self.config["target_model"] = models[0]

    # -------------------------------------------------------------------------
    # UI EVENT HANDLERS
    # -------------------------------------------------------------------------

    def on_stack_selected(self, stack_name: str) -> None:
        """Update extension filters based on a stack preset."""
        if stack_name in const.DEFAULT_STACKS:
            extensions = const.DEFAULT_STACKS[stack_name]
            self.settings_view.entry_ext.delete(0, "end")
            self.settings_view.entry_ext.insert(0, ",".join(extensions))
            self.config["extensions"] = extensions

    def on_tree_toggled(self) -> None:
        """Dynamic UI visibility logic for AST analysis options."""
        if self.dashboard_view.sw_tree.get():
            # Ruff E501: Wrapped grid configuration
            self.dashboard_view.frame_ast.grid(
                row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10)
            )
        else:
            self.dashboard_view.frame_ast.grid_forget()

    def on_skeleton_toggled(self) -> None:
        """Handle skeleton mode state changes from the Dashboard."""
        self.sync_config_from_view()
        logger.debug(f"Skeleton Mode updated: {self.config['processing_depth']}")

    def reset_config(self) -> None:
        """Revert the current session to factory defaults."""
        if mb.askyesno(i18n.t("gui.dialogs.confirm_title"), "Reset all settings to defaults?"):
            self.config = cfg.get_default_config()
            self.sync_view_from_config()
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings reset.")

    def purge_cache(self) -> None:
        """Manually clear the local processing cache database."""
        if mb.askyesno("Purge Cache", "Clear the local processing cache?"):
            try:
                self.cache_service.purge_all()
                mb.showinfo("Cache Cleared", "Local cache has been successfully purged.")
            except Exception as e:
                logger.error(f"Failed to purge cache: {e}")
                mb.showerror("Error", f"Failed to purge cache:\n{e}")

    def on_model_selected(self, model_name: str) -> None:
        """Update session state silently and log selection."""
        self.config["target_model"] = model_name
        logger.info(f"UI: Model context switched to '{model_name}'.")

    # -------------------------------------------------------------------------
    # DELEGATED ACTIONS
    # -------------------------------------------------------------------------

    def load_profile(self) -> None:
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        self.profile_controller.delete_profile()

    def request_feedback(self) -> None:
        self.feedback_controller.on_feedback_requested()