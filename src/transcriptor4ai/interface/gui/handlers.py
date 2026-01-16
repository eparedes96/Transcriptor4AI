from __future__ import annotations

"""
Event handlers and logic controllers for the GUI.

This module implements the 'Controller' part of the MVC pattern.
It handles user interactions, dialogs, modals, and configuration management
using CustomTkinter components.
"""

import logging
import os
import platform
import subprocess
import threading
import tkinter.messagebox as mb
import webbrowser
from typing import List, Dict, Any, Optional, Tuple, cast

import customtkinter as ctk

from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra.logging import get_recent_logs
from transcriptor4ai.interface.gui import threads
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# OS System Helpers
# -----------------------------------------------------------------------------
def open_file_explorer(path: str) -> None:
    """
    Open the host OS file explorer at the given path.
    Supports Windows, macOS, and Linux (xdg-open).

    Args:
        path: Directory path to open.
    """
    if not os.path.exists(path):
        logger.warning(f"Attempted to open non-existent path: {path}")
        mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.popups.error_path", path=path))
        return
    try:
        sys_name = platform.system()
        if sys_name == "Windows":
            os.startfile(path)
        elif sys_name == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        logger.error(f"Failed to open file explorer: {e}")
        mb.showerror(i18n.t("gui.dialogs.error_title"), f"Could not open folder:\n{e}")


def parse_list_from_string(value: Optional[str]) -> List[str]:
    """
    Convert a comma-separated string to a list of stripped strings.

    Args:
        value: Input CSV string (e.g., ".py, .js").

    Returns:
        List of strings (e.g., [".py", ".js"]). Returns empty list on None.
    """
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


# -----------------------------------------------------------------------------
# Main Application Controller
# -----------------------------------------------------------------------------
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

    # --- View Management ---
    def register_views(self, dashboard: Any, settings: Any, logs: Any, sidebar: Any) -> None:
        """Link view frames to the controller."""
        self.dashboard_view = dashboard
        self.settings_view = settings
        self.logs_view = logs
        self.sidebar_view = sidebar

    def sync_view_from_config(self) -> None:
        """Populate UI widgets with values from self.config."""
        if not self.dashboard_view: return

        input_path = self.config.get("input_path", "")
        output_path = self.config.get("output_base_dir", "")

        # If output path is undefined in config, default to input path
        if not output_path:
            output_path = input_path

        self._safe_entry_update(self.dashboard_view.entry_input, input_path)
        self._safe_entry_update(self.dashboard_view.entry_output, output_path)

        self.dashboard_view.entry_subdir.delete(0, "end")
        self.dashboard_view.entry_subdir.insert(0, self.config.get("output_subdir_name", ""))
        self.dashboard_view.entry_prefix.delete(0, "end")
        self.dashboard_view.entry_prefix.insert(0, self.config.get("output_prefix", ""))

        self._set_switch(self.dashboard_view.sw_modules, "process_modules")
        self._set_switch(self.dashboard_view.sw_tests, "process_tests")
        self._set_switch(self.dashboard_view.sw_resources, "process_resources")
        self._set_switch(self.dashboard_view.sw_tree, "generate_tree")

        # AST State Check
        self.on_tree_toggled()

        # AST Checkboxes
        self._set_checkbox(self.dashboard_view.chk_func, "show_functions")
        self._set_checkbox(self.dashboard_view.chk_class, "show_classes")
        self._set_checkbox(self.dashboard_view.chk_meth, "show_methods")

        # Settings
        self.settings_view.entry_ext.delete(0, "end")
        self.settings_view.entry_ext.insert(0, ",".join(self.config.get("extensions", [])))
        self.settings_view.entry_inc.delete(0, "end")
        self.settings_view.entry_inc.insert(0, ",".join(self.config.get("include_patterns", [])))
        self.settings_view.entry_exc.delete(0, "end")
        self.settings_view.entry_exc.insert(0, ",".join(self.config.get("exclude_patterns", [])))

        self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))
        self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))

        target_model = self.config.get("target_model", cfg.DEFAULT_MODEL_KEY)

        # 1. Determine Provider from Model
        current_provider = "OPENAI"
        if target_model in cfg.AI_MODELS:
            current_provider = cfg.AI_MODELS[target_model].get("provider", "OPENAI")

        # 2. Populate Provider Combo
        providers = sorted(list(set(m["provider"] for m in cfg.AI_MODELS.values())))
        self.settings_view.combo_provider.configure(values=providers)
        self.settings_view.combo_provider.set(current_provider)

        # 3. Populate Model Combo based on Provider
        self._filter_models_by_provider(current_provider, preserve_selection=target_model)

        self._set_switch(self.settings_view.sw_gitignore, "respect_gitignore")
        self._set_switch(self.settings_view.sw_individual, "create_individual_files")
        self._set_switch(self.settings_view.sw_unified, "create_unified_file")
        self._set_switch(self.settings_view.sw_sanitizer, "enable_sanitizer")
        self._set_switch(self.settings_view.sw_mask, "mask_user_paths")
        self._set_switch(self.settings_view.sw_minify, "minify_output")
        self._set_switch(self.settings_view.sw_error_log, "save_error_log")

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
        # Filter models belonging to this provider
        models = sorted([name for name, data in cfg.AI_MODELS.items() if data.get("provider") == provider])

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

    def sync_config_from_view(self) -> None:
        """Scrape values from UI widgets into self.config."""
        if not self.dashboard_view: return

        # Dashboard
        self.config["input_path"] = self.dashboard_view.entry_input.get().strip()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get().strip()
        self.config["output_subdir_name"] = self.dashboard_view.entry_subdir.get().strip()
        self.config["output_prefix"] = self.dashboard_view.entry_prefix.get().strip()

        self.config["process_modules"] = bool(self.dashboard_view.sw_modules.get())
        self.config["process_tests"] = bool(self.dashboard_view.sw_tests.get())
        self.config["process_resources"] = bool(self.dashboard_view.sw_resources.get())
        self.config["generate_tree"] = bool(self.dashboard_view.sw_tree.get())

        # AST
        self.config["show_functions"] = bool(self.dashboard_view.chk_func.get())
        self.config["show_classes"] = bool(self.dashboard_view.chk_class.get())
        self.config["show_methods"] = bool(self.dashboard_view.chk_meth.get())

        # Settings
        self.config["extensions"] = parse_list_from_string(self.settings_view.entry_ext.get())
        self.config["include_patterns"] = parse_list_from_string(self.settings_view.entry_inc.get())
        self.config["exclude_patterns"] = parse_list_from_string(self.settings_view.entry_exc.get())

        # Model Selector
        self.config["target_model"] = self.settings_view.combo_model.get()

        self.config["respect_gitignore"] = bool(self.settings_view.sw_gitignore.get())
        self.config["create_individual_files"] = bool(self.settings_view.sw_individual.get())
        self.config["create_unified_file"] = bool(self.settings_view.sw_unified.get())
        self.config["enable_sanitizer"] = bool(self.settings_view.sw_sanitizer.get())
        self.config["mask_user_paths"] = bool(self.settings_view.sw_mask.get())
        self.config["minify_output"] = bool(self.settings_view.sw_minify.get())
        self.config["save_error_log"] = bool(self.settings_view.sw_error_log.get())

    # --- Actions ---
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
                msg = i18n.t("gui.popups.overwrite_msg", files="\n".join(result.existing_files))
                if mb.askyesno(i18n.t("gui.popups.overwrite_title"), msg):
                    self.start_processing(dry_run=False, overwrite=True)
                    return

        self._toggle_ui(disabled=False)
        self.dashboard_view.btn_process.configure(text=i18n.t("gui.dashboard.btn_start"), fg_color="#007ACC")

        if isinstance(result, PipelineResult):
            if result.ok:
                show_results_window(self.app, result)
            else:
                mb.showerror(i18n.t("gui.dialogs.pipeline_failed"), result.error)
        elif isinstance(result, Exception):
            show_crash_modal(str(result), "See logs for details.", self.app)

    def _toggle_ui(self, disabled: bool) -> None:
        state = "disabled" if disabled else "normal"
        self.dashboard_view.btn_process.configure(state=state)
        self.dashboard_view.btn_simulate.configure(state=state)

    def on_stack_selected(self, stack_name: str) -> None:
        """Update extension field when a stack preset is chosen."""
        if stack_name in cfg.DEFAULT_STACKS:
            extensions = cfg.DEFAULT_STACKS[stack_name]
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

        if model_name == cfg.DEFAULT_MODEL_KEY:
            return

        # Inform user that actual inference is not active, only estimation
        logger.info(i18n.t("gui.logs.api_warning", model=model_name))

        model_info = cfg.AI_MODELS.get(model_name, {})
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

    def load_profile(self) -> None:
        name = self.settings_view.combo_profiles.get()
        if name == i18n.t("gui.profiles.no_selection"): return

        profiles = self.app_state.get("saved_profiles", {})
        if name in profiles:
            temp = cfg.get_default_config()
            temp.update(profiles[name])
            self.config.update(temp)
            self.sync_view_from_config()
            self.settings_view.combo_stack.set(i18n.t("gui.combos.select_stack"))
            mb.showinfo(i18n.t("gui.dialogs.success_title"), f"Profile '{name}' loaded.")

    def save_profile(self) -> None:
        dialog = ctk.CTkInputDialog(text=i18n.t("gui.profiles.prompt_name"), title="Save Profile")
        name = dialog.get_input()
        if name:
            name = name.strip()
            profiles = self.app_state.get("saved_profiles", {})
            if name in profiles:
                if not mb.askyesno(
                        i18n.t("gui.profiles.confirm_overwrite_title"),
                        i18n.t("gui.profiles.confirm_overwrite_msg", name=name)
                ):
                    return

            self.sync_config_from_view()
            self.app_state.setdefault("saved_profiles", {})[name] = self.config.copy()
            cfg.save_app_state(self.app_state)
            self._update_profile_list(name)
            mb.showinfo(i18n.t("gui.dialogs.saved_title"), i18n.t("gui.profiles.saved", name=name))

    def delete_profile(self) -> None:
        name = self.settings_view.combo_profiles.get()
        if name == i18n.t("gui.profiles.no_selection"): return

        profiles = self.app_state.get("saved_profiles", {})
        if name in profiles:
            if mb.askyesno(i18n.t("gui.dialogs.confirm_title"), i18n.t("gui.profiles.confirm_delete", name=name)):
                del profiles[name]
                cfg.save_app_state(self.app_state)
                self._update_profile_list()

    def _update_profile_list(self, select_name: str = "") -> None:
        names = sorted(list(self.app_state.get("saved_profiles", {}).keys()))
        self.settings_view.combo_profiles.configure(values=names)
        if select_name:
            self.settings_view.combo_profiles.set(select_name)
        elif names:
            self.settings_view.combo_profiles.set(names[0])
        else:
            self.settings_view.combo_profiles.set(i18n.t("gui.profiles.no_selection"))


# -----------------------------------------------------------------------------
# Modal Dialogs
# -----------------------------------------------------------------------------
def show_results_window(parent: ctk.CTk, result: PipelineResult) -> None:
    """Display execution results in a Toplevel window."""
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.popups.title_result"))
    toplevel.geometry("600x500")
    toplevel.grab_set()

    summary = result.summary or {}
    dry_run = summary.get("dry_run", False)
    header = i18n.t("gui.results_window.dry_run_header") if dry_run else i18n.t("gui.results_window.success_header")
    color = "#F0AD4E" if dry_run else "#2CC985"

    # Header
    ctk.CTkLabel(
        toplevel, text=header,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=color
    ).pack(pady=20)

    # Stats
    stats_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    stats_frame.pack(pady=10)
    ctk.CTkLabel(stats_frame,
                 text=f"{i18n.t('gui.results_window.stats_processed')}: {summary.get('processed', 0)}").pack()
    ctk.CTkLabel(stats_frame, text=f"{i18n.t('gui.results_window.stats_skipped')}: {summary.get('skipped', 0)}").pack()
    ctk.CTkLabel(stats_frame, text=f"{i18n.t('gui.results_window.stats_tokens')}: {result.token_count:,}").pack()

    ctk.CTkLabel(toplevel, text=i18n.t("gui.results_window.files_label")).pack(pady=(20, 5))
    scroll_frame = ctk.CTkScrollableFrame(toplevel, height=150)
    scroll_frame.pack(fill="x", padx=20)

    gen_files = summary.get("generated_files", {})
    unified_path = gen_files.get("unified")

    for key, path in gen_files.items():
        if path:
            name = os.path.basename(path)
            ctk.CTkLabel(scroll_frame, text=f"[{key.upper()}] {name}", anchor="w").pack(fill="x", padx=5)

    # Actions
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(pady=20, fill="x", padx=20)

    def _open() -> None:
        open_file_explorer(result.final_output_path)

    def _copy() -> None:
        if unified_path and os.path.exists(unified_path):
            try:
                with open(unified_path, "r", encoding="utf-8") as f:
                    parent.clipboard_clear()
                    parent.clipboard_append(f.read())
                mb.showinfo(i18n.t("gui.results_window.copied_msg"), "Unified content copied to clipboard.")
            except Exception as e:
                mb.showerror(i18n.t("gui.dialogs.error_title"), str(e))

    ctk.CTkButton(btn_frame, text=i18n.t("gui.results_window.btn_open"), command=_open).pack(side="left", expand=True,
                                                                                             padx=5)

    copy_btn = ctk.CTkButton(btn_frame, text=i18n.t("gui.results_window.btn_copy"), command=_copy)
    copy_btn.pack(side="left", expand=True, padx=5)
    if dry_run or not unified_path:
        copy_btn.configure(state="disabled")

    ctk.CTkButton(btn_frame, text=i18n.t("gui.results_window.btn_close"), fg_color="transparent", border_width=1,
                  text_color=("gray10", "#DCE4EE"),
                  command=toplevel.destroy).pack(side="left", expand=True, padx=5)


# -----------------------------------------------------------------------------
# Feedback & Crash Reporting
# -----------------------------------------------------------------------------
def show_feedback_window(parent: ctk.CTk) -> None:
    """Display the Feedback Hub modal window."""
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Feedback Hub")
    toplevel.geometry("500x550")
    toplevel.resizable(False, False)
    toplevel.grab_set()

    # Header
    ctk.CTkLabel(
        toplevel,
        text="Send Feedback",
        font=ctk.CTkFont(size=20, weight="bold")
    ).pack(pady=(20, 5))

    ctk.CTkLabel(
        toplevel,
        text="Help us improve Transcriptor4AI.",
        text_color="gray"
    ).pack(pady=(0, 20))

    content_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    content_frame.pack(fill="x", padx=20)

    # Type Selector
    ctk.CTkLabel(content_frame, text=i18n.t("gui.feedback.type_label"), anchor="w").pack(fill="x")
    report_types = ["Bug Report", "Feature Request", "Other"]
    report_type = ctk.CTkComboBox(content_frame, values=report_types, state="readonly")
    report_type.set(report_types[0])
    report_type.pack(fill="x", pady=(0, 10))

    # Subject
    ctk.CTkLabel(content_frame, text="Subject:", anchor="w").pack(fill="x")
    subject = ctk.CTkEntry(content_frame)
    subject.pack(fill="x", pady=(0, 10))

    # Message
    ctk.CTkLabel(content_frame, text="Message:", anchor="w").pack(fill="x")
    msg = ctk.CTkTextbox(content_frame, height=150)
    msg.pack(fill="x", pady=(0, 10))

    # Logs Checkbox
    chk_logs = ctk.CTkCheckBox(content_frame, text="Include recent logs", onvalue=True, offvalue=False)
    chk_logs.select()
    chk_logs.pack(anchor="w", pady=(0, 20))

    # Status Label
    status_lbl = ctk.CTkLabel(toplevel, text="", text_color="gray")
    status_lbl.pack(pady=(0, 5))

    def _on_sent(result: Tuple[bool, str]) -> None:
        success, message = result
        btn_send.configure(state="normal")

        if success:
            mb.showinfo(i18n.t("gui.dialogs.success_title"), "Thank you! Your feedback has been sent.")
            toplevel.destroy()
        else:
            status_lbl.configure(text=f"Error: {message}", text_color="#D9534F")
            mb.showerror(i18n.t("gui.dialogs.error_title"), f"Failed to send feedback:\n{message}")

    def _send() -> None:
        if not subject.get().strip() or not msg.get("1.0", "end").strip():
            mb.showerror(i18n.t("gui.dialogs.error_title"), "Please fill in Subject and Message.")
            return

        btn_send.configure(state="disabled")
        status_lbl.configure(text="Sending feedback...", text_color="#007ACC")

        payload = {
            "type": report_type.get(),
            "subject": subject.get(),
            "message": msg.get("1.0", "end"),
            "version": cfg.CURRENT_CONFIG_VERSION,
            "os": platform.system(),
            "logs": get_recent_logs(100) if chk_logs.get() else ""
        }

        # Background submission
        threading.Thread(
            target=threads.submit_feedback_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_sent(res))),
            daemon=True
        ).start()

    # Footer Actions
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=10)

    btn_cancel = ctk.CTkButton(
        btn_frame,
        text="Cancel",
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", "#DCE4EE"),
        command=toplevel.destroy
    )
    btn_cancel.pack(side="left", expand=True, padx=5)

    btn_send = ctk.CTkButton(
        btn_frame,
        text="Send Feedback",
        fg_color="#007ACC",
        command=_send
    )
    btn_send.pack(side="left", expand=True, padx=5)


def show_crash_modal(error_msg: str, stack_trace: str, parent: Optional[ctk.CTk] = None) -> None:
    """
    Display critical error details with reporting capability.
    """
    is_root_created = False
    if parent is None:
        parent = ctk.CTk()
        parent.withdraw()
        is_root_created = True

    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.crash.title"))
    toplevel.geometry("700x600")
    toplevel.grab_set()

    ctk.CTkLabel(
        toplevel,
        text=i18n.t("gui.crash.header"),
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#D9534F"
    ).pack(pady=(20, 10))

    ctk.CTkLabel(toplevel, text="The application has encountered an unexpected problem.").pack()

    # Traceback Area
    textbox = ctk.CTkTextbox(toplevel, font=("Consolas", 10), height=200)
    textbox.insert("1.0", f"Error: {error_msg}\n\n{stack_trace}")
    textbox.configure(state="disabled")
    textbox.pack(fill="both", expand=True, padx=20, pady=10)

    # User Context
    ctk.CTkLabel(toplevel, text="What were you doing? (Optional):", anchor="w").pack(fill="x", padx=20)
    user_comment = ctk.CTkTextbox(toplevel, height=60)
    user_comment.pack(fill="x", padx=20, pady=(0, 10))

    status_lbl = ctk.CTkLabel(toplevel, text="", text_color="gray", font=("Any", 10))
    status_lbl.pack(pady=(0, 5))

    def _on_reported(result: Tuple[bool, str]) -> None:
        success, message = result
        btn_report.configure(state="normal")
        if success:
            status_lbl.configure(text="Report sent successfully. Thank you.", text_color="green")
            mb.showinfo("Report Sent", "Error report submitted. We will investigate this issue.")
            if is_root_created:
                parent.destroy()
            else:
                toplevel.destroy()
        else:
            status_lbl.configure(text="Failed to send report.", text_color="red")
            mb.showerror("Submission Error", f"Could not send report:\n{message}")

    def _send_report() -> None:
        btn_report.configure(state="disabled")
        status_lbl.configure(text="Sending report...", text_color="#007ACC")

        payload = {
            "error": error_msg,
            "stack_trace": stack_trace,
            "user_comment": user_comment.get("1.0", "end"),
            "app_version": cfg.CURRENT_CONFIG_VERSION,
            "os": platform.system(),
            "logs": get_recent_logs(150)
        }

        threading.Thread(
            target=threads.submit_error_report_task,
            args=(payload, lambda res: parent.after(0, lambda: _on_reported(res))),
            daemon=True
        ).start()

    def _close() -> None:
        if is_root_created:
            parent.destroy()
        else:
            toplevel.destroy()

    # Buttons
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=20)

    ctk.CTkButton(
        btn_frame,
        text="Copy Error",
        command=lambda: parent.clipboard_append(f"Error: {error_msg}\n\n{stack_trace}")
    ).pack(side="left", padx=5)

    btn_report = ctk.CTkButton(
        btn_frame,
        text="Send Error Report",
        fg_color="#2CC985",
        hover_color="#229965",
        command=_send_report
    )
    btn_report.pack(side="left", padx=5, expand=True)

    ctk.CTkButton(
        btn_frame,
        text="Close",
        fg_color="#D9534F",
        hover_color="#C9302C",
        command=_close
    ).pack(side="right", padx=5)

    if is_root_created:
        parent.mainloop()


def show_update_prompt_modal(
        parent: ctk.CTk,
        latest_version: str,
        changelog: str,
        binary_url: str,
        dest_path: str,
        browser_url: str = ""
) -> bool:
    """
    Shows a modal for updates. Returns True if user accepts OTA download.
    """
    if not mb.askyesno(
            i18n.t("gui.dialogs.update_title"),
            f"Version v{latest_version} is available.\n\nDownload now?"
    ):
        return False

    if binary_url and dest_path:
        return True
    else:
        webbrowser.open(browser_url)
        return False