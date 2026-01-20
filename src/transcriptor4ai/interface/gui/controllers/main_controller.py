from __future__ import annotations

"""
Main Application Controller.

Bridges the View (UI Components) and the Model (Core Logic).
Handles user interactions, configuration sync, and process execution.
Acts as a Facade for specialized sub-controllers (Profiles, Feedback),
managing the asynchronous lifecycle of the transcription pipeline.
Integrates CacheService management (Purge) and Financial Cost logic.
"""

import logging
import os
import threading
import tkinter.messagebox as mb
from typing import Any, Dict, List, Optional, Tuple

import customtkinter as ctk

from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.estimator import CostEstimator
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.domain import constants as const
from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.interface.gui.controllers.feedback_controller import FeedbackController
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController
from transcriptor4ai.interface.gui.dialogs import crash_modal, results_modal
from transcriptor4ai.interface.gui.utils import tk_helpers
from transcriptor4ai.interface.gui.utils.binder import FormBinder
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)

# ==============================================================================
# PRIMARY APPLICATION CONTROLLER
# ==============================================================================

class AppController:
    """
    Central controller class that bridges the UI (View) and the Core (Model).

    It manages the application state, configuration syncing via declarative
    mappings, and thread-safe event handling for long-running tasks.
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
        self.cost_estimator = CostEstimator()
        self.cache_service = CacheService()

        # Initialize Sub-Controllers (Delegation Pattern)
        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)

    # -------------------------------------------------------------------------
    # VIEW REGISTRATION
    # -------------------------------------------------------------------------

    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
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

        Delegates widget manipulation to FormBinder and resolves
        provider-specific model dependencies.
        """
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. IO Paths (Read-only logic handled by Binder)
        input_path = self.config.get("input_path", "")
        output_path = self.config.get("output_base_dir", "") or input_path
        self.binder.update_entry(self.dashboard_view.entry_input, input_path)
        self.binder.update_entry(self.dashboard_view.entry_output, output_path)

        # 2. Generic Declarative Mapping
        mapping = self.binder.get_ui_mapping(self.dashboard_view, self.settings_view)

        for key, widget in mapping.get("switches", []):
            self.binder.set_switch_state(self.config, widget, key)

        for key, widget in mapping.get("checkboxes", []):
            self.binder.set_checkbox_state(self.config, widget, key)

        for key, widget in mapping.get("entries", []):
            widget.delete(0, "end")
            widget.insert(0, str(self.config.get(key, "")))

        # 3. List Fields (CSV format)
        list_fields: List[Tuple[str, ctk.CTkEntry]] = [
            ("extensions", self.settings_view.entry_ext),
            ("include_patterns", self.settings_view.entry_inc),
            ("exclude_patterns", self.settings_view.entry_exc)
        ]
        for key, widget in list_fields:
            widget.delete(0, "end")
            widget.insert(0, ",".join(self.config.get(key, [])))

        # 4. ComboBoxes and UI States
        self.on_tree_toggled()
        self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model = self.config.get("target_model", const.DEFAULT_MODEL_KEY)

        # Determine Provider context from current model
        current_provider = "OPENAI"
        if target_model in const.AI_MODELS:
            current_provider = const.AI_MODELS[target_model].get("provider", "OPENAI")

        providers = sorted(list(set(m["provider"] for m in const.AI_MODELS.values())))
        self.settings_view.combo_provider.configure(values=providers)
        self.settings_view.combo_provider.set(current_provider)

        self._filter_models_by_provider(current_provider, preserve_selection=target_model)

        # Reset financial display on config sync
        if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
            self.dashboard_view.update_cost_display(0.0)

    def sync_config_from_view(self) -> None:
        """
        Scrape current UI widget values into the internal configuration state.

        Standardizes data types (CSV strings to lists, 0/1 to bool) before
        updating the transient session config.
        """
        if not self.dashboard_view or not self.settings_view:
            return

        # 1. IO Paths
        self.config["input_path"] = self.dashboard_view.entry_input.get().strip()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get().strip()

        # 2. Map generic fields
        mapping = self.binder.get_ui_mapping(self.dashboard_view, self.settings_view)

        for key, widget in mapping.get("switches", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("checkboxes", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("entries", []):
            self.config[key] = widget.get().strip()

        # 3. List transformation
        self.config["extensions"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_ext.get()
        )
        self.config["include_patterns"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_inc.get()
        )
        self.config["exclude_patterns"] = tk_helpers.parse_list_from_string(
            self.settings_view.entry_exc.get()
        )

        # 4. AI Strategy
        self.config["target_model"] = self.settings_view.combo_model.get()

    # -------------------------------------------------------------------------
    # CORE PIPELINE EXECUTION
    # -------------------------------------------------------------------------

    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        """
        Initiate the transcription pipeline in a background thread.

        Performs pre-flight validation and manages UI state transitions.

        Args:
            dry_run: Enable simulation mode.
            overwrite: Permission to replace existing artifacts.
        """
        self.sync_config_from_view()

        input_path = self.config.get("input_path", "")
        if not os.path.isdir(input_path):
            mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.dialogs.invalid_input"))
            return

        # UI State transition to locked/processing
        self._toggle_ui(disabled=True)
        btn_text = i18n.t("gui.dashboard.btn_simulating") if dry_run else "PROCESSING..."
        self.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        self._cancellation_event.clear()

        logger.debug(f"Starting pipeline (DryRun={dry_run}). Config: {self.config}")

        # Dispatch execution to background thread to maintain GUI responsiveness
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
        """Process pipeline result, managing collisions and error reporting."""
        if isinstance(result, PipelineResult) and not result.ok:
            if result.existing_files:
                msg = i18n.t("gui.popups.overwrite_msg", files="/n".join(result.existing_files))
                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    self.start_processing(dry_run=False, overwrite=True)
                    return

        # UI State transition back to normal
        self._toggle_ui(disabled=False)
        self.dashboard_view.btn_process.configure(
            text=i18n.t("gui.dashboard.btn_start"),
            fg_color="#1F6AA5"
        )

        # Result orchestration and Financial Calculation
        if isinstance(result, PipelineResult):
            if result.ok:
                target_model = self.config.get("target_model", const.DEFAULT_MODEL_KEY)
                cost = self.cost_estimator.calculate_cost(result.token_count, target_model)

                if self.dashboard_view and hasattr(self.dashboard_view, "update_cost_display"):
                    self.dashboard_view.update_cost_display(cost)

                results_modal.show_results_window(self.app, result)
            else:
                if self._cancellation_event.is_set() and "cancelled" in result.error.lower():
                    logger.info("Pipeline stopped by user signal.")
                else:
                    mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)
        elif isinstance(result, Exception):
            crash_modal.show_crash_modal(str(result), "See logs for details.", self.app)

    def _toggle_ui(self, disabled: bool) -> None:
        """Helper to enable/disable interaction during processing."""
        state = "disabled" if disabled else "normal"
        self.dashboard_view.btn_process.configure(state=state)
        self.dashboard_view.btn_simulate.configure(state=state)

    # -------------------------------------------------------------------------
    # PRICING SYNCHRONIZATION
    # -------------------------------------------------------------------------

    def on_pricing_updated(self, data: Optional[Dict[str, Any]]) -> None:
        """
        Handle remote pricing data delivery from the network thread.

        Args:
            data: Retrieved pricing dictionary or None if sync failed.
        """
        if data:
            self.cost_estimator.update_live_pricing(data)
            if self.dashboard_view and hasattr(self.dashboard_view, "set_pricing_status"):
                self.dashboard_view.set_pricing_status(is_live=True)
        else:
            logger.warning("Controller: Pricing sync failed. Fallback to cached constants active.")
            if self.dashboard_view and hasattr(self.dashboard_view, "set_pricing_status"):
                self.dashboard_view.set_pricing_status(is_live=False)

    # -------------------------------------------------------------------------
    # UI EVENT HANDLERS
    # -------------------------------------------------------------------------

    def on_provider_selected(self, provider: str) -> None:
        """Update the model selection list when the provider changes."""
        self._filter_models_by_provider(provider)
        new_model = self.settings_view.combo_model.get()
        self.config["target_model"] = new_model
        self.on_model_selected(new_model)

    def _filter_models_by_provider(
            self,
            provider: str,
            preserve_selection: Optional[str] = None
    ) -> None:
        """Filter the model ComboBox values based on selected provider."""
        models = sorted([n for n, d in const.AI_MODELS.items() if d.get("provider") == provider])

        if not models:
            models = ["-- No Models --"]

        self.settings_view.combo_model.configure(values=models)

        if preserve_selection and preserve_selection in models:
            self.settings_view.combo_model.set(preserve_selection)
        else:
            self.settings_view.combo_model.set(models[0])
            self.config["target_model"] = models[0]

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
            self.dashboard_view.frame_ast.grid(
                row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10)
            )
        else:
            self.dashboard_view.frame_ast.grid_forget()

    def reset_config(self) -> None:
        """Revert the current session to factory defaults."""
        if mb.askyesno(i18n.t("gui.dialogs.confirm_title"),
                       "Are you sure you want to reset all settings to their defaults?"):
            self.config = cfg.get_default_config()
            self.sync_view_from_config()
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings have been reset.")

    def purge_cache(self) -> None:
        """
        Manually clear the local cache database.

        Invoked by the user via Settings to resolve potential cache corruption
        or force a fresh processing cycle.
        """
        if mb.askyesno("Purge Cache", "Are you sure you want to clear the local processing cache?"):
            try:
                self.cache_service.purge_all()
                mb.showinfo("Cache Cleared", "Local cache has been successfully purged.")
            except Exception as e:
                logger.error(f"Controller: Failed to purge cache: {e}")
                mb.showerror("Error", f"Failed to purge cache:/n{e}")

    def on_model_selected(self, model_name: str) -> None:
        """Update session state and perform security key verification."""
        self.config["target_model"] = model_name

        if model_name == const.DEFAULT_MODEL_KEY:
            return

        # Inform user that actual inference is not active, only estimation
        logger.info(i18n.t("gui.logs.api_warning", model=model_name))

        model_info = const.AI_MODELS.get(model_name, {})
        provider = model_info.get("provider", "")

        # Environment security verification for accurate tokenization
        missing_key = False
        if provider == "GOOGLE" and not os.environ.get("GOOGLE_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but GOOGLE_API_KEY is missing.")
        elif provider == "ANTHROPIC" and not os.environ.get("ANTHROPIC_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but ANTHROPIC_API_KEY is missing.")
        elif provider == "MISTRAL" and not os.environ.get("MISTRAL_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but MISTRAL_API_KEY is missing.")

        if missing_key:
            logger.warning(f"Selected {model_name} but API key is missing.")
            mb.showwarning(
                i18n.t("gui.dialogs.warning_title"),
                "Missing API Key for accurate token count./nUsing heuristic fallback."
            )

    # -------------------------------------------------------------------------
    # DELEGATED ACTIONS (SUB-CONTROLLERS)
    # -------------------------------------------------------------------------

    def load_profile(self) -> None:
        """Delegate profile loading."""
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        """Delegate profile saving."""
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        """Delegate profile deletion."""
        self.profile_controller.delete_profile()

    def request_feedback(self) -> None:
        """Delegate feedback trigger."""
        self.feedback_controller.on_feedback_requested()