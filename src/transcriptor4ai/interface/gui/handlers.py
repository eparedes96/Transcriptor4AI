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
from typing import List, Dict, Any, Optional, Tuple

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
        mb.showerror("Error", f"Could not open folder:\n{e}")


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

        # Shortcuts to Views (Populated by app.py)
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

        # Dashboard
        self.dashboard_view.entry_input.delete(0, "end")
        self.dashboard_view.entry_input.insert(0, self.config.get("input_path", ""))
        self.dashboard_view.entry_output.delete(0, "end")
        self.dashboard_view.entry_output.insert(0, self.config.get("output_base_dir", ""))
        self.dashboard_view.entry_subdir.delete(0, "end")
        self.dashboard_view.entry_subdir.insert(0, self.config.get("output_subdir_name", ""))
        self.dashboard_view.entry_prefix.delete(0, "end")
        self.dashboard_view.entry_prefix.insert(0, self.config.get("output_prefix", ""))

        if self.config.get("process_modules"):
            self.dashboard_view.sw_modules.select()
        else:
            self.dashboard_view.sw_modules.deselect()

        if self.config.get("process_tests"):
            self.dashboard_view.sw_tests.select()
        else:
            self.dashboard_view.sw_tests.deselect()

        if self.config.get("process_resources"):
            self.dashboard_view.sw_resources.select()
        else:
            self.dashboard_view.sw_resources.deselect()

        if self.config.get("generate_tree"):
            self.dashboard_view.sw_tree.select()
        else:
            self.dashboard_view.sw_tree.deselect()

        # Settings
        self.settings_view.entry_ext.delete(0, "end")
        self.settings_view.entry_ext.insert(0, ",".join(self.config.get("extensions", [])))
        self.settings_view.entry_inc.delete(0, "end")
        self.settings_view.entry_inc.insert(0, ",".join(self.config.get("include_patterns", [])))
        self.settings_view.entry_exc.delete(0, "end")
        self.settings_view.entry_exc.insert(0, ",".join(self.config.get("exclude_patterns", [])))

        self._set_switch(self.settings_view.sw_gitignore, "respect_gitignore")
        self._set_switch(self.settings_view.sw_individual, "create_individual_files")
        self._set_switch(self.settings_view.sw_unified, "create_unified_file")
        self._set_switch(self.settings_view.sw_sanitizer, "enable_sanitizer")
        self._set_switch(self.settings_view.sw_mask, "mask_user_paths")
        self._set_switch(self.settings_view.sw_minify, "minify_output")

    def _set_switch(self, switch: ctk.CTkSwitch, key: str) -> None:
        if self.config.get(key):
            switch.select()
        else:
            switch.deselect()

    def sync_config_from_view(self) -> None:
        """Scrape values from UI widgets into self.config."""
        if not self.dashboard_view: return

        # Dashboard
        self.config["input_path"] = self.dashboard_view.entry_input.get()
        self.config["output_base_dir"] = self.dashboard_view.entry_output.get()
        self.config["output_subdir_name"] = self.dashboard_view.entry_subdir.get()
        self.config["output_prefix"] = self.dashboard_view.entry_prefix.get()

        self.config["process_modules"] = bool(self.dashboard_view.sw_modules.get())
        self.config["process_tests"] = bool(self.dashboard_view.sw_tests.get())
        self.config["process_resources"] = bool(self.dashboard_view.sw_resources.get())
        self.config["generate_tree"] = bool(self.dashboard_view.sw_tree.get())

        # Settings
        self.config["extensions"] = parse_list_from_string(self.settings_view.entry_ext.get())
        self.config["include_patterns"] = parse_list_from_string(self.settings_view.entry_inc.get())
        self.config["exclude_patterns"] = parse_list_from_string(self.settings_view.entry_exc.get())

        self.config["respect_gitignore"] = bool(self.settings_view.sw_gitignore.get())
        self.config["create_individual_files"] = bool(self.settings_view.sw_individual.get())
        self.config["create_unified_file"] = bool(self.settings_view.sw_unified.get())
        self.config["enable_sanitizer"] = bool(self.settings_view.sw_sanitizer.get())
        self.config["mask_user_paths"] = bool(self.settings_view.sw_mask.get())
        self.config["minify_output"] = bool(self.settings_view.sw_minify.get())

    # --- Actions ---
    def start_processing(self, dry_run: bool = False) -> None:
        self.sync_config_from_view()

        if not os.path.isdir(self.config["input_path"]):
            mb.showerror("Error", "Invalid Input Directory")
            return

        self._toggle_ui(disabled=True)
        btn_text = "SIMULATING..." if dry_run else "PROCESSING..."
        self.dashboard_view.btn_process.configure(text=btn_text, fg_color="gray")

        self._cancellation_event.clear()

        # Start thread
        threading.Thread(
            target=threads.run_pipeline_task,
            args=(self.config, False, dry_run, self._on_process_complete, self._cancellation_event),
            daemon=True
        ).start()

    def _on_process_complete(self, result: Any) -> None:
        """Callback executed when the pipeline thread finishes."""
        # Use .after to ensure thread-safety with Tkinter main loop
        self.app.after(0, lambda: self._handle_process_result(result))

    def _handle_process_result(self, result: Any) -> None:
        self._toggle_ui(disabled=False)
        self.dashboard_view.btn_process.configure(text="START PROCESSING", fg_color="#007ACC")

        if isinstance(result, PipelineResult):
            if result.ok:
                show_results_window(self.app, result)
            else:
                mb.showerror("Pipeline Failed", result.error)
        elif isinstance(result, Exception):
            show_crash_modal(self.app, str(result), "See logs for details.")

    def _toggle_ui(self, disabled: bool) -> None:
        state = "disabled" if disabled else "normal"
        self.dashboard_view.btn_process.configure(state=state)
        self.dashboard_view.btn_simulate.configure(state=state)

    # --- Profile Management ---
    def load_profile(self) -> None:
        name = self.settings_view.combo_profiles.get()
        profiles = self.app_state.get("saved_profiles", {})
        if name in profiles:
            temp = cfg.get_default_config()
            temp.update(profiles[name])
            self.config.update(temp)
            self.sync_view_from_config()
            mb.showinfo("Success", f"Profile '{name}' loaded.")

    def save_profile(self) -> None:
        dialog = ctk.CTkInputDialog(text="Enter profile name:", title="Save Profile")
        name = dialog.get_input()
        if name:
            name = name.strip()
            self.sync_config_from_view()
            self.app_state.setdefault("saved_profiles", {})[name] = self.config.copy()
            cfg.save_app_state(self.app_state)
            self._update_profile_list(name)
            mb.showinfo("Saved", f"Profile '{name}' saved.")

    def delete_profile(self) -> None:
        name = self.settings_view.combo_profiles.get()
        profiles = self.app_state.get("saved_profiles", {})
        if name in profiles:
            if mb.askyesno("Confirm", f"Delete profile '{name}'?"):
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
            self.settings_view.combo_profiles.set("")


# -----------------------------------------------------------------------------
# Modal Dialogs
# -----------------------------------------------------------------------------

def show_results_window(parent: ctk.CTk, result: PipelineResult) -> None:
    """Display execution results in a Toplevel window."""
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Execution Result")
    toplevel.geometry("600x500")
    toplevel.grab_set()  # Make modal

    summary = result.summary or {}
    dry_run = summary.get("dry_run", False)
    header = "SIMULATION COMPLETE" if dry_run else "PROCESS COMPLETED"
    color = "#007ACC" if dry_run else "#2CC985"

    # Header
    ctk.CTkLabel(
        toplevel, text=header,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=color
    ).pack(pady=20)

    # Stats
    stats_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    stats_frame.pack(pady=10)
    ctk.CTkLabel(stats_frame, text=f"Processed: {summary.get('processed', 0)}").pack()
    ctk.CTkLabel(stats_frame, text=f"Skipped: {summary.get('skipped', 0)}").pack()
    ctk.CTkLabel(stats_frame, text=f"Est. Tokens: {result.token_count:,}").pack()

    # Files List
    ctk.CTkLabel(toplevel, text="Generated Files:").pack(pady=(20, 5))
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

    def _open():
        open_file_explorer(result.final_output_path)

    def _copy():
        if unified_path and os.path.exists(unified_path):
            try:
                with open(unified_path, "r", encoding="utf-8") as f:
                    parent.clipboard_clear()
                    parent.clipboard_append(f.read())
                mb.showinfo("Copied", "Unified content copied to clipboard.")
            except Exception as e:
                mb.showerror("Error", str(e))

    ctk.CTkButton(btn_frame, text="Open Folder", command=_open).pack(side="left", expand=True, padx=5)

    copy_btn = ctk.CTkButton(btn_frame, text="Copy Unified", command=_copy)
    copy_btn.pack(side="left", expand=True, padx=5)
    if dry_run or not unified_path:
        copy_btn.configure(state="disabled")

    ctk.CTkButton(btn_frame, text="Close", fg_color="transparent", border_width=1,
                  command=toplevel.destroy).pack(side="left", expand=True, padx=5)


def show_crash_modal(parent: ctk.CTk, error_msg: str, stack_trace: str) -> None:
    """Display critical error details."""
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title("Critical Error")
    toplevel.geometry("700x500")
    toplevel.grab_set()

    ctk.CTkLabel(
        toplevel, text="CRITICAL ERROR DETECTED",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#D9534F"
    ).pack(pady=20)

    textbox = ctk.CTkTextbox(toplevel, font=("Consolas", 10))
    textbox.insert("1.0", f"Error: {error_msg}\n\n{stack_trace}")
    textbox.configure(state="disabled")
    textbox.pack(fill="both", expand=True, padx=20, pady=10)

    def _send_report():
        payload = {
            "error": error_msg,
            "stack_trace": stack_trace,
            "os": platform.system(),
            "logs": get_recent_logs(100)
        }

        # Simple feedback simulation
        mb.showinfo("Report", "Report feature is being upgraded for V2.0.\nLog data has been preserved.")

    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(fill="x", padx=20, pady=20)

    ctk.CTkButton(btn_frame, text="Send Report", fg_color="green", command=_send_report).pack(side="left", padx=10)
    ctk.CTkButton(btn_frame, text="Close", fg_color="#D9534F", command=toplevel.destroy).pack(side="right", padx=10)


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
    Note: In V2.0 Architecture, this is handled via Sidebar badge, but we keep
    logic for explicit checks.
    """
    if not mb.askyesno(
            "Update Available",
            f"Version v{latest_version} is available.\n\nDownload now?"
    ):
        return False

    if binary_url and dest_path:
        return True
    else:
        webbrowser.open(browser_url)
        return False