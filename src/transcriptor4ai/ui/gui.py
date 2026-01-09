from __future__ import annotations

"""
Graphical User Interface (GUI) for transcriptor4ai.

Implemented using PySimpleGUI. Manages user interactions, threaded 
pipeline execution, persistent configuration, and community feedback.
Ensures semantic layout for AST options and update lifecycle management.
"""

import logging
import os
import platform
import subprocess
import threading
import traceback
import webbrowser
from typing import Any, Dict, List, Optional

import PySimpleGUI as sg

from transcriptor4ai import config as cfg
from transcriptor4ai import paths
from transcriptor4ai.logging import (
    configure_logging,
    LoggingConfig,
    get_default_gui_log_path,
    get_recent_logs
)
from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.pipeline import run_pipeline, PipelineResult
from transcriptor4ai.utils.i18n import i18n
from transcriptor4ai.utils import network

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Threading Helpers
# -----------------------------------------------------------------------------
def _run_pipeline_thread(
        window: sg.Window,
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool
) -> None:
    """Execute the pipeline in a background thread and signal the window."""
    try:
        result = run_pipeline(config, overwrite=overwrite, dry_run=dry_run)
        window.write_event_value("-THREAD-DONE-", result)
    except Exception as e:
        logger.critical(f"Critical failure in pipeline thread: {e}", exc_info=True)
        window.write_event_value("-THREAD-DONE-", e)


def _check_updates_thread(window: sg.Window, is_manual: bool = False) -> None:
    """
    Check for updates in a background thread.

    Args:
        window: The GUI window instance.
        is_manual: Whether the check was triggered by user action.
    """
    res = network.check_for_updates(cfg.CURRENT_CONFIG_VERSION)
    # Always send event to handle manual feedback
    window.write_event_value("-UPDATE-FINISHED-", (res, is_manual))


def _submit_feedback_thread(window: sg.Window, payload: Dict[str, Any]) -> None:
    """Submit feedback in a background thread."""
    success, msg = network.submit_feedback(payload)
    window.write_event_value("-FEEDBACK-SUBMITTED-", (success, msg))


# -----------------------------------------------------------------------------
# System Helpers
# -----------------------------------------------------------------------------
def _open_file_explorer(path: str) -> None:
    """Open the host OS file explorer at the given path."""
    if not os.path.exists(path):
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
        sg.popup_error(f"Could not open folder:\n{e}")


def _parse_list_from_string(value: str) -> List[str]:
    """Convert CSV string to list of stripped strings."""
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


# -----------------------------------------------------------------------------
# Community & Feedback Windows
# -----------------------------------------------------------------------------
def show_feedback_window() -> None:
    """Display the Feedback Hub modal window."""
    layout = [
        [sg.Text("Feedback Hub", font=("Any", 14, "bold"))],
        [sg.Text("Help us improve Transcriptor4AI with your suggestions or bug reports.")],
        [sg.Text("Type:"), sg.Combo(["Bug Report", "Feature Request", "Other"], key="-FB_TYPE-", readonly=True,
                                    default_value="Bug Report")],
        [sg.Text("Subject:"), sg.Input(key="-FB_SUB-", expand_x=True)],
        [sg.Text("Message:")],
        [sg.Multiline(key="-FB_MSG-", size=(60, 10), expand_x=True)],
        [sg.Checkbox("Include recent logs (Recommended for bugs)", key="-FB_LOGS-", default=True)],
        [
            sg.Button("Send Feedback", key="-SEND_FB-", button_color="green"),
            sg.Button("Cancel", key="-CANCEL_FB-")
        ],
        [sg.Text("", key="-FB_STATUS-", visible=False)]
    ]

    fb_window = sg.Window("Send Feedback", layout, modal=True, finalize=True)

    while True:
        event, values = fb_window.read()
        if event in (sg.WIN_CLOSED, "-CANCEL_FB-"):
            break

        if event == "-SEND_FB-":
            if not values["-FB_SUB-"] or not values["-FB_MSG-"]:
                sg.popup_error("Please fill in both Subject and Message.")
                continue

            fb_window["-SEND_FB-"].update(disabled=True)
            fb_window["-FB_STATUS-"].update("Sending...", visible=True, text_color="blue")

            payload = {
                "type": values["-FB_TYPE-"],
                "subject": values["-FB_SUB-"],
                "message": values["-FB_MSG-"],
                "version": cfg.CURRENT_CONFIG_VERSION,
                "os": platform.system()
            }
            if values["-FB_LOGS-"]:
                payload["logs"] = get_recent_logs(100)

            threading.Thread(target=_submit_feedback_thread, args=(fb_window, payload), daemon=True).start()

        if event == "-FEEDBACK-SUBMITTED-":
            success, msg = values[event]
            if success:
                sg.popup("Thank you! Your feedback has been sent.")
                break
            else:
                sg.popup_error(f"Failed to send feedback:\n{msg}")
                fb_window["-SEND_FB-"].update(disabled=False)
                fb_window["-FB_STATUS-"].update("Error", text_color="red")

    fb_window.close()


def show_crash_modal(error_msg: str, stack_trace: str) -> None:
    """Display a technical modal for critical unhandled exceptions."""
    layout = [
        [sg.Text("⚠️ Critical Error Detected", font=("Any", 14, "bold"), text_color="red")],
        [sg.Text("The application has encountered an unexpected problem.")],
        [sg.Multiline(f"Error: {error_msg}\n\n{stack_trace}", size=(70, 15), font=("Courier", 8), readonly=True)],
        [
            sg.Button("Copy to Clipboard", key="-COPY_ERR-"),
            sg.Button("Close", key="-EXIT_ERR-")
        ]
    ]
    window = sg.Window("Crash Reporter", layout, modal=True)
    while True:
        event, _ = window.read()
        if event in (sg.WIN_CLOSED, "-EXIT_ERR-"):
            break
        if event == "-COPY_ERR-":
            sg.clipboard_set(stack_trace)
            sg.popup_quick_message("Copied!")
    window.close()


# -----------------------------------------------------------------------------
# Results Window
# -----------------------------------------------------------------------------
def _show_results_window(result: PipelineResult) -> None:
    """Show detailed pipeline execution summary and metrics."""
    summary = result.summary or {}
    dry_run = summary.get("dry_run", False)
    header_text = i18n.t("gui.results_window.dry_run_header") if dry_run else i18n.t(
        "gui.results_window.success_header")
    header_color = "#007ACC" if dry_run else "green"
    icon_char = "ℹ" if dry_run else "✔"

    stats_layout = [
        [sg.Text(f"{i18n.t('gui.results_window.stats_processed')}:", size=(15, 1)),
         sg.Text(f"{summary.get('processed', 0)}", text_color="white")],
        [sg.Text(f"{i18n.t('gui.results_window.stats_skipped')}:", size=(15, 1)),
         sg.Text(f"{summary.get('skipped', 0)}", text_color="yellow")],
        [sg.Text(f"{i18n.t('gui.results_window.stats_errors')}:", size=(15, 1)),
         sg.Text(f"{summary.get('errors', 0)}", text_color="red" if summary.get('errors', 0) > 0 else "gray")],
        [sg.HorizontalSeparator()],
        [sg.Text("Est. Tokens:", size=(15, 1), font=("Any", 10, "bold")),
         sg.Text(f"{result.token_count:,}", text_color="#569CD6", font=("Any", 10, "bold"))]
    ]

    gen_files = summary.get("generated_files", {})
    files_list = []
    unified_path = gen_files.get("unified")
    has_unified = bool(unified_path and os.path.exists(unified_path))

    for key, path in gen_files.items():
        if path:
            files_list.append(f"[{key.upper()}] {os.path.basename(path)}")

    tree_info = summary.get("tree", {})
    if tree_info.get("generated") and tree_info.get("path"):
        files_list.append(f"[TREE] {os.path.basename(tree_info.get('path'))} ({tree_info.get('lines')} lines)")

    layout = [
        [sg.Text(icon_char, font=("Any", 24), text_color=header_color),
         sg.Text(header_text, font=("Any", 14, "bold"), text_color=header_color)],
        [sg.HorizontalSeparator()],
        [sg.Column(stats_layout)],
        [sg.Text(i18n.t("gui.results_window.files_label"))],
        [sg.Listbox(values=files_list, size=(60, 6), key="-FILES_LIST-", expand_x=True)],
        [sg.Text(result.final_output_path, font=("Any", 8), text_color="gray")],
        [sg.HorizontalSeparator()],
        [
            sg.Button(i18n.t("gui.results_window.btn_open"), key="-OPEN-"),
            sg.Button(i18n.t("gui.results_window.btn_copy"), key="-COPY-", disabled=(not has_unified or dry_run)),
            sg.Push(),
            sg.Button(i18n.t("gui.results_window.btn_close"), key="-CLOSE-", button_color=("white", "red"))
        ]
    ]
    res_window = sg.Window(i18n.t("gui.results_window.title"), layout, modal=True, finalize=True)
    while True:
        event, _ = res_window.read()
        if event in (sg.WIN_CLOSED, "-CLOSE-"):
            break
        if event == "-OPEN-":
            _open_file_explorer(result.final_output_path)
        if event == "-COPY-":
            if has_unified:
                try:
                    with open(unified_path, "r", encoding="utf-8") as f:
                        sg.clipboard_set(f.read())
                    sg.popup_quick_message(i18n.t("gui.results_window.copied_msg"))
                except Exception as e:
                    sg.popup_error(f"Copy failed: {e}")
    res_window.close()


# -----------------------------------------------------------------------------
# GUI Config Helpers
# -----------------------------------------------------------------------------
def update_config_from_gui(config: Dict[str, Any], values: Dict[str, Any]) -> None:
    """Synchronize UI values back to the config dictionary."""
    for k in ["input_path", "output_base_dir", "output_subdir_name", "output_prefix", "target_model"]:
        config[k] = values.get(k)
    for k in ["process_modules", "process_tests", "process_resources", "generate_tree",
              "create_individual_files", "create_unified_file", "show_functions",
              "show_classes", "show_methods", "print_tree", "save_error_log", "respect_gitignore"]:
        config[k] = bool(values.get(k))

    config["extensions"] = _parse_list_from_string(values.get("extensions", ""))
    config["include_patterns"] = _parse_list_from_string(values.get("include_patterns", ""))
    config["exclude_patterns"] = _parse_list_from_string(values.get("exclude_patterns", ""))


def populate_gui_from_config(window: sg.Window, config: Dict[str, Any]) -> None:
    """Populate UI fields from a config dictionary."""
    keys = ["input_path", "output_base_dir", "output_subdir_name", "output_prefix",
            "process_modules", "process_tests", "generate_tree", "create_individual_files",
            "create_unified_file", "show_functions", "show_classes", "show_methods",
            "print_tree", "save_error_log", "respect_gitignore"]
    for k in keys:
        if k in window.AllKeysDict:
            window[k].update(config.get(k))

    window["process_resources"].update(config.get("process_resources", False))
    window["target_model"].update(config.get("target_model", "GPT-4o / GPT-5"))
    window["extensions"].update(",".join(config.get("extensions", [])))
    window["include_patterns"].update(",".join(config.get("include_patterns", [])))
    window["exclude_patterns"].update(",".join(config.get("exclude_patterns", [])))


def _toggle_ui_state(window: sg.Window, is_disabled: bool) -> None:
    """Enable or disable interactive elements during long operations."""
    keys = ["btn_process", "btn_simulate", "btn_reset", "btn_browse_in", "btn_browse_out",
            "btn_load_profile", "btn_save_profile", "btn_del_profile", "btn_feedback"]
    for key in keys:
        if key in window.AllKeysDict:
            window[key].update(disabled=is_disabled)


# -----------------------------------------------------------------------------
# Main GUI Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    """Main GUI Application loop."""
    log_path = get_default_gui_log_path()
    configure_logging(LoggingConfig(level="INFO", console=True, log_file=log_path))
    logger.info(f"GUI Starting - Version {cfg.CURRENT_CONFIG_VERSION}")
    sg.theme("SystemDefault")

    try:
        app_state = cfg.load_app_state()
        config = cfg.load_config()
        saved_profiles = app_state.get("saved_profiles", {})
        profile_names = sorted(list(saved_profiles.keys()))
    except Exception as e:
        logger.error(f"State load failed: {e}")
        app_state = cfg.get_default_app_state()
        config = cfg.get_default_config()
        profile_names = []

    # --- Layout Definitions ---
    menu_def = [['&File', ['&Reset Config', '---', 'E&xit']],
                ['&Community', ['&Send Feedback', '&Check for Updates']],
                ['&Help', ['&About']]]

    frame_profiles = [[
        sg.Text(i18n.t("gui.labels.profile"), font=("Any", 8)),
        sg.Combo(values=profile_names, key="-PROFILE_LIST-", size=(20, 1), readonly=True),
        sg.Button(i18n.t("gui.profiles.load"), key="btn_load_profile", font=("Any", 8)),
        sg.Button(i18n.t("gui.profiles.save"), key="btn_save_profile", font=("Any", 8)),
        sg.Button(i18n.t("gui.profiles.del"), key="btn_del_profile", font=("Any", 8), button_color="gray"),
        sg.Push(),
        sg.Button("Feedback Hub", key="btn_feedback", button_color=("white", "#4A90E2"), font=("Any", 8, "bold"))
    ]]

    # Content selection layout with hierarchical Tree/AST grouping
    frame_content = [
        [
            sg.Checkbox(i18n.t("gui.checkboxes.modules"), key="process_modules", default=config["process_modules"]),
            sg.Checkbox(i18n.t("gui.checkboxes.tests"), key="process_tests", default=config["process_tests"]),
            sg.Checkbox("Resources (.md, .json...)", key="process_resources",
                        default=config.get("process_resources", False)),
        ],
        [
            sg.Checkbox(i18n.t("gui.checkboxes.gen_tree"), key="generate_tree", default=config["generate_tree"],
                        enable_events=True),
            sg.Text(" └─ AST symbols:", font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.func"), key="show_functions", default=config["show_functions"],
                        font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.cls"), key="show_classes", default=config["show_classes"],
                        font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.meth"), key="show_methods", default=config["show_methods"],
                        font=("Any", 8)),
        ]
    ]

    layout = [
        [sg.Menu(menu_def)],
        [sg.Column(frame_profiles, expand_x=True)],
        [sg.HorizontalSeparator()],
        [sg.Text(i18n.t("gui.sections.input"))],
        [sg.Input(default_text=config["input_path"], key="input_path", expand_x=True),
         sg.Button(i18n.t("gui.buttons.explore"), key="btn_browse_in")],
        [sg.Text(i18n.t("gui.sections.output"))],
        [sg.Input(default_text=config["output_base_dir"], key="output_base_dir", expand_x=True),
         sg.Button(i18n.t("gui.buttons.examine"), key="btn_browse_out")],
        [
            sg.Text(i18n.t("gui.sections.sub_output")),
            sg.Input(config["output_subdir_name"], size=(15, 1), key="output_subdir_name"),
            sg.Text(i18n.t("gui.sections.prefix")),
            sg.Input(config["output_prefix"], size=(15, 1), key="output_prefix"),
        ],
        [sg.Frame(i18n.t("gui.sections.content"), frame_content, expand_x=True)],
        [sg.Frame(i18n.t("gui.sections.format"), [[
            sg.Checkbox(i18n.t("gui.checkboxes.individual"), key="create_individual_files",
                        default=config["create_individual_files"]),
            sg.Checkbox(i18n.t("gui.checkboxes.unified"), key="create_unified_file",
                        default=config["create_unified_file"]),
        ]], expand_x=True)],
        [sg.Text("Extension Stack:", font=("Any", 8, "bold")),
         sg.Combo(["-- Select --"] + sorted(list(cfg.DEFAULT_STACKS.keys())), key="-STACK-", enable_events=True,
                  readonly=True),
         sg.Text("Target Model:", font=("Any", 8, "bold")),
         sg.Combo(["GPT-4o / GPT-5", "Claude 3.5", "Gemini Pro"], key="target_model",
                  default_value=config.get("target_model"), readonly=True)],
        [sg.Text("Extensions:"), sg.Input(",".join(config["extensions"]), key="extensions", expand_x=True)],
        [sg.Text("Include:"), sg.Input(",".join(config["include_patterns"]), key="include_patterns", expand_x=True)],
        [sg.Text("Exclude:"), sg.Input(",".join(config["exclude_patterns"]), key="exclude_patterns", expand_x=True)],
        [sg.Checkbox("Respect .gitignore", key="respect_gitignore", default=config.get("respect_gitignore", True)),
         sg.Checkbox("Save error log", key="save_error_log", default=config["save_error_log"])],
        [sg.Text("", key="-STATUS-", visible=False, font=("Any", 10, "bold"))],
        [
            sg.Button(i18n.t("gui.buttons.simulate"), key="btn_simulate", button_color=("white", "#007ACC")),
            sg.Button(i18n.t("gui.buttons.process"), key="btn_process", button_color=("white", "green")),
            sg.Push(),
            sg.Button(i18n.t("gui.buttons.reset"), key="btn_reset"),
            sg.Button(i18n.t("gui.buttons.exit"), key="btn_exit", button_color=("white", "red")),
        ],
        [sg.Text(f"v{cfg.CURRENT_CONFIG_VERSION}", font=("Any", 7), text_color="gray"), sg.Push(),
         sg.Text("", key="-UPDATE_BAR-", font=("Any", 7), text_color="blue", enable_events=True)]
    ]

    window = sg.Window(f"Transcriptor4AI - v{cfg.CURRENT_CONFIG_VERSION}", layout, finalize=True, resizable=True)

    # --- Start Background Tasks ---
    if app_state["app_settings"].get("auto_check_updates"):
        threading.Thread(target=_check_updates_thread, args=(window, False), daemon=True).start()

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "btn_exit", "Exit"):
            if values:
                update_config_from_gui(config, values)
                app_state["last_session"] = config
                cfg.save_app_state(app_state)
            break

        # --- Community Events ---
        if event in ("btn_feedback", "Send Feedback"):
            show_feedback_window()

        if event == "Check for Updates":
            window["-UPDATE_BAR-"].update("Checking...")
            threading.Thread(target=_check_updates_thread, args=(window, True), daemon=True).start()

        if event == "-UPDATE-FINISHED-":
            res, is_manual = values[event]

            if res.get("has_update"):
                msg = f"New version available: v{res['latest_version']}. Click to download."
                window["-UPDATE_BAR-"].update(msg)
                if sg.popup_yes_no(
                        f"A new version (v{res['latest_version']}) is available!\n\n{res['changelog']}\n\nOpen download page?") == "Yes":
                    webbrowser.open(res["download_url"])
            elif is_manual:
                window["-UPDATE_BAR-"].update("Up to date.")
                sg.popup(f"Transcriptor4AI is up to date (v{cfg.CURRENT_CONFIG_VERSION}).")
            else:
                window["-UPDATE_BAR-"].update("")

        # --- Standard Events ---
        if event == "generate_tree":
            enabled = bool(values["generate_tree"])
            for k in ["show_functions", "show_classes", "show_methods"]:
                window[k].update(disabled=not enabled)

        if event == "-STACK-":
            stack = values["-STACK-"]
            if stack in cfg.DEFAULT_STACKS:
                window["extensions"].update(",".join(cfg.DEFAULT_STACKS[stack]))

        if event == "btn_browse_in":
            folder = sg.popup_get_folder("Select Input", default_path=values["input_path"])
            if folder:
                window["input_path"].update(folder)

        if event == "btn_browse_out":
            folder = sg.popup_get_folder("Select Output", default_path=values["output_base_dir"])
            if folder:
                window["output_base_dir"].update(folder)

        if event in ("btn_process", "btn_simulate"):
            is_sim = (event == "btn_simulate")
            update_config_from_gui(config, values)

            # Basic Validation
            if not os.path.isdir(config["input_path"]):
                sg.popup_error("Invalid input directory.")
                continue

            _toggle_ui_state(window, True)
            window["-STATUS-"].update("SIMULATING..." if is_sim else "PROCESSING...", visible=True,
                                      text_color="#007ACC" if is_sim else "blue")
            threading.Thread(target=_run_pipeline_thread, args=(window, config, True, is_sim), daemon=True).start()

        if event == "-THREAD-DONE-":
            _toggle_ui_state(window, False)
            window["-STATUS-"].update(visible=False)
            res = values[event]
            if isinstance(res, PipelineResult):
                if res.ok:
                    _show_results_window(res)
                else:
                    sg.popup_error(f"Error: {res.error}")
            elif isinstance(res, Exception):
                tb = traceback.format_exc()
                show_crash_modal(str(res), tb)

    window.close()


if __name__ == "__main__":
    main()