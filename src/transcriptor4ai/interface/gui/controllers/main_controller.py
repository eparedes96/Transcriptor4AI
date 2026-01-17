from __future__ import annotations

"""
Main Application Controller.

Bridges the View (UI Components) and the Model (Core Logic).
Handles user interactions, configuration sync, and process execution.
Acts as a Facade for specialized sub-controllers (Profiles, Feedback).
"""

import logging
import os
import threading
import tkinter.messagebox as mb
from typing import Dict, Any, Optional, List, Tuple

import customtkinter as ctk

from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.domain import constants as const
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.interface.gui.dialogs import results_modal, crash_modal
from transcriptor4ai.interface.gui.utils import tk_helpers
from transcriptor4ai.utils.i18n import i18n

# Sub-controllers
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController
from transcriptor4ai.interface.gui.controllers.feedback_controller import FeedbackController

logger = logging.getLogger(__name__)


class AppController:
    """
    Central controller class that bridges the UI (View) and the Core (Model).
    It manages the application state, configuration syncing, and event handling.
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
        self._cancellation_event = threading.Event()

        # Shortcuts to Views
        self.dashboard_view: Any = None
        self.settings_view: Any = None
        self.logs_view: Any = None
        self.sidebar_view: Any = None

        # Initialize Sub-Controllers (Delegation Pattern)
        self.profile_controller = ProfileController(self)
        self.feedback_controller = FeedbackController(self)

    # -------------------------------------------------------------------------
    # View Management
    # -------------------------------------------------------------------------
    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
        """Link view frames to the controller."""
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    def _get_ui_mapping(self) -> Dict[str, List[Tuple[str, Any]]]:
        """
        Returns a declarative mapping of config keys to UI components.
        Organized by component type to simplify iteration.
        """
        if not self.dashboard_view or not self.settings_view:
            return {}

        return {
            "switches": [
                ("process_modules", self.dashboard_view.sw_modules),
                ("process_tests", self.dashboard_view.sw_tests),
                ("process_resources", self.dashboard_view.sw_resources),
                ("generate_tree", self.dashboard_view.sw_tree),
                ("respect_gitignore", self.settings_view.sw_gitignore),
                ("create_individual_files", self.settings_view.sw_individual),
                ("create_unified_file", self.settings_view.sw_unified),
                ("enable_sanitizer", self.settings_view.sw_sanitizer),
                ("mask_user_paths", self.settings_view.sw_mask),
                ("minify_output", self.settings_view.sw_minify),
                ("save_error_log", self.settings_view.sw_error_log),
            ],
            "checkboxes": [
                ("show_functions", self.dashboard_view.chk_func),
                ("show_classes", self.dashboard_view.chk_class),
                ("show_methods", self.dashboard_view.chk_meth),
            ],
            "entries": [
                ("output_subdir_name", self.dashboard_view.entry_subdir),
                ("output_prefix", self.dashboard_view.entry_prefix),
            ]
        }

    def sync_view_from_config(self) -> None:
        """Populate UI widgets with values from self.config using declarative mapping."""
        if not self.dashboard_view:
            return

        # 1. Rutas (Lógica especial por ser ReadOnly)
        input_path = self.config.get("input_path", "")
        output_path = self.config.get("output_base_dir", "") or input_path
        self._safe_entry_update(self.dashboard_view.entry_input, input_path)
        self._safe_entry_update(self.dashboard_view.entry_output, output_path)

        # 2. Mapeo genérico
        mapping = self._get_ui_mapping()

        for key, widget in mapping.get("switches", []):
            self._set_switch(widget, key)

        for key, widget in mapping.get("checkboxes", []):
            self._set_checkbox(widget, key)

        for key, widget in mapping.get("entries", []):
            widget.delete(0, "end")
            widget.insert(0, str(self.config.get(key, "")))

        # 3. Campos de lista (Settings)
        for key, widget in [("extensions", self.settings_view.entry_ext),
                            ("include_patterns", self.settings_view.entry_inc),
                            ("exclude_patterns", self.settings_view.entry_exc)]:
            widget.delete(0, "end")
            widget.insert(0, ",".join(self.config.get(key, [])))

        # 4. Combos y estados visuales
        self.on_tree_toggled()
        self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model = self.config.get("target_model", const.DEFAULT_MODEL_KEY)

        # 1. Determine Provider from Model
        current_provider = "OPENAI"
        if target_model in const.AI_MODELS:
            current_provider = const.AI_MODELS[target_model].get("provider", "OPENAI")

        # 2. Populate Provider Combo
        providers = sorted(list(set(m["provider"] for m in const.AI_MODELS.values())))
        self.settings_view.combo_provider.configure(values=providers)
        self.settings_view.combo_provider.set(current_provider)

        # 3. Populate Model Combo based on Provider
        self._filter_models_by_provider(current_provider, preserve_selection=target_model)

    def sync_config_from_view(self) -> None:
        """Scrape values from UI widgets into self.config using declarative mapping."""
        if not self.dashboard_view:
            return

        # 1. Rutas y campos básicos
        self.config["input_path"] = self.dashboard_view.entry_input.get().strip()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get().strip()

        # 2. Mapeo genérico
        mapping = self._get_ui_mapping()

        for key, widget in mapping.get("switches", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("checkboxes", []):
            self.config[key] = bool(widget.get())

        for key, widget in mapping.get("entries", []):
            self.config[key] = widget.get().strip()

        # 3. Listas
        self.config["extensions"] = tk_helpers.parse_list_from_string(self.settings_view.entry_ext.get())
        self.config["include_patterns"] = tk_helpers.parse_list_from_string(self.settings_view.entry_inc.get())
        self.config["exclude_patterns"] = tk_helpers.parse_list_from_string(self.settings_view.entry_exc.get())

        # 4. Otros
        self.config["target_model"] = self.settings_view.combo_model.get()

    def on_provider_selected(self, provider: str) -> None:
        """Callback triggered when the Provider Combobox changes."""
        self._filter_models_by_provider(provider)

        # Automatically select the first model available for this provider
        new_model = self.settings_view.combo_model.get()
        self.config["target_model"] = new_model
        self.on_model_selected(new_model)

    def _filter_models_by_provider(self, provider: str, preserve_selection: Optional[str] = None) -> None:
        """
        Update the Model Combobox values based on the selected provider.
        """
        models = sorted([name for name, data in const.AI_MODELS.items() if data.get("provider") == provider])

        if not models:
            models = ["-- No Models --"]

        self.settings_view.combo_model.configure(values=models)

        # Logic to set the current selection
        if preserve_selection and preserve_selection in models:
            self.settings_view.combo_model.set(preserve_selection)
        else:
            self.settings_view.combo_model.set(models[0])
            self.config["target_model"] = models[0]

    def _safe_entry_update(self, entry: ctk.CTkEntry, text: str) -> None:
        """Helper to update readonly entries."""
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, text)
        entry.configure(state="readonly")

    def _set_switch(self, switch: ctk.CTkSwitch, key: str) -> None:
        if self.config.get(key):
            switch.select()
        else:
            switch.deselect()

    def _set_checkbox(self, chk: ctk.CTkCheckBox, key: str) -> None:
        if self.config.get(key):
            chk.select()
        else:
            chk.deselect()

    def start_processing(self, dry_run: bool = False, overwrite: bool = False) -> None:
        self.sync_config_from_view()

        input_path = self.config.get("input_path", "")
        if not os.path.isdir(input_path):
            mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.dialogs.invalid_input"))
            return

        self._toggle_ui(disabled=True)
        btn_text = i18n.t("gui.dashboard.btn_simulating") if dry_run else "PROCESSING..."
        self.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        self._cancellation_event.clear()

        # Debug log to verify data integrity before core execution
        logger.debug(f"Starting pipeline (DryRun={dry_run}). Config Payload: {self.config}")

        # Start thread
        threading.Thread(
            target=threads.run_pipeline_task,
            args=(self.config, overwrite, dry_run, self._on_process_complete, self._cancellation_event),
            daemon=True
        ).start()

    def _on_process_complete(self, result: Any) -> None:
        """Callback executed when the pipeline thread finishes."""
        self.app.after(0, lambda: self._handle_process_result(result))

    def _handle_process_result(self, result: Any) -> None:
        if isinstance(result, PipelineResult) and not result.ok:
            if result.existing_files:
                msg = i18n.t("gui.popups.overwrite_msg", files="/n".join(result.existing_files))
                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    self.start_processing(dry_run=False, overwrite=True)
                    return

        self._toggle_ui(disabled=False)
        self.dashboard_view.btn_process.configure(text=i18n.t("gui.dashboard.btn_start"), fg_color="#1f538d")

        if isinstance(result, PipelineResult):
            if result.ok:
                results_modal.show_results_window(self.app, result)
            else:
                mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)
        elif isinstance(result, Exception):
            crash_modal.show_crash_modal(str(result), "See logs for details.", self.app)

    def _toggle_ui(self, disabled: bool) -> None:
        state = "disabled" if disabled else "normal"
        self.dashboard_view.btn_process.configure(state=state)
        self.dashboard_view.btn_simulate.configure(state=state)

    # -------------------------------------------------------------------------
    # UI Logic & Helpers
    # -------------------------------------------------------------------------
    def on_stack_selected(self, stack_name: str) -> None:
        """Update extension field when a stack preset is chosen."""
        if stack_name in const.DEFAULT_STACKS:
            extensions = const.DEFAULT_STACKS[stack_name]
            self.settings_view.entry_ext.delete(0, "end")
            self.settings_view.entry_ext.insert(0, ",".join(extensions))
            self.config["extensions"] = extensions

    def on_tree_toggled(self) -> None:
        """Show/Hide AST options based on Tree Switch state."""
        if self.dashboard_view.sw_tree.get():
            self.dashboard_view.frame_ast.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        else:
            self.dashboard_view.frame_ast.grid_forget()

    def reset_config(self) -> None:
        """Reset the current configuration to factory defaults."""
        if mb.askyesno(i18n.t("gui.dialogs.confirm_title"),
                       "Are you sure you want to reset all settings to their defaults?"):
            self.config = cfg.get_default_config()
            self.sync_view_from_config()
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Settings have been reset to default.")

    def on_model_selected(self, model_name: str) -> None:
        """Update config and check for API keys (Phase 12.2)."""
        self.config["target_model"] = model_name

        if model_name == const.DEFAULT_MODEL_KEY:
            return

        # Inform user that actual inference is not active, only estimation
        logger.info(i18n.t("gui.logs.api_warning", model=model_name))

        model_info = const.AI_MODELS.get(model_name, {})
        provider = model_info.get("provider", "")

        # Security/Environment Check
        missing_key = False
        if provider == "GOOGLE" and not os.environ.get("GOOGLE_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but GOOGLE_API_KEY is missing.")
        elif provider == "ANTHROPIC" and not os.environ.get("ANTHROPIC_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but ANTHROPIC_API_KEY is missing.")
        elif (provider == "MISTRAL" or provider == "MISTRAL_VISION") and not os.environ.get("MISTRAL_API_KEY"):
            missing_key = True
            logger.warning(f"Selected {model_name} but MISTRAL_API_KEY is missing.")

        if missing_key:
            mb.showwarning(
                i18n.t("gui.dialogs.warning_title"),
                "Missing API Key for accurate token count.\nUsing heuristic fallback."
            )

    # -------------------------------------------------------------------------
    # Delegated Profile Actions
    # -------------------------------------------------------------------------
    def load_profile(self) -> None:
        self.profile_controller.load_profile()

    def save_profile(self) -> None:
        self.profile_controller.save_profile()

    def delete_profile(self) -> None:
        self.profile_controller.delete_profile()

    # -------------------------------------------------------------------------
    # Delegated Feedback Actions
    # -------------------------------------------------------------------------
    def request_feedback(self) -> None:
        self.feedback_controller.on_feedback_requested()