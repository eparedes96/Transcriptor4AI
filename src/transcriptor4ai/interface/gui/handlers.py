from __future__ import annotations

"""
Event handlers and logic controllers for the GUI.

This module implements the 'Controller' part of the MVC pattern.
It handles user interactions, dialogs, modals, and configuration management.
"""

import logging
import os
import platform
import subprocess
import threading
import webbrowser
from typing import List, Dict, Any, Optional

import PySimpleGUI as sg

from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra.logging import get_recent_logs
from transcriptor4ai.interface.gui.threads import (
    download_update_task,
    submit_feedback_task,
    submit_error_report_task
)
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
        sg.popup_error(f"Could not open folder:\n{e}")


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
# Modal Dialogs (Interaction Logic)
# -----------------------------------------------------------------------------
def show_update_prompt_modal(
        parent_window: sg.Window,
        latest_version: str,
        changelog: str,
        binary_url: str,
        dest_path: str,
        browser_url: str = ""
) -> bool:
    """
    Display a modal asking the user to confirm an update.

    Args:
        parent_window: The main application window (for progress updates).
        latest_version: Version string of the new release.
        changelog: Text description of changes.
        binary_url: Direct download URL (OTA).
        dest_path: Local path target for download.
        browser_url: Fallback URL for manual download.

    Returns:
        bool: True if OTA download started, False otherwise.
    """
    is_ota_viable = bool(binary_url and dest_path)

    instruction = (
        "A new update is ready. Would you like to download it now?"
        if is_ota_viable else
        "A new version is available. Background download is not available for this release."
    )

    btn_text = "Yes, Download" if is_ota_viable else "Go to GitHub"
    btn_color = "green" if is_ota_viable else "#007ACC"

    layout = [
        [sg.Text(f"New version available: v{latest_version}", font=("Any", 11, "bold"))],
        [sg.Text(instruction)],
        [sg.Multiline(
            changelog,
            size=(70, 15),
            font=("Courier", 9),
            disabled=True,
            background_color="#F0F0F0",
            no_scrollbar=False
        )],
        [sg.Push(),
         sg.Button(btn_text, key="-YES-", button_color=btn_color, size=(15, 1)),
         sg.Button("Not now", key="-NO-", size=(12, 1))]
    ]

    window = sg.Window("Software Update", layout, modal=True, finalize=True, element_justification='left')

    result = False
    while True:
        event, _ = window.read()
        if event in (sg.WIN_CLOSED, "-NO-"):
            result = False
            break
        if event == "-YES-":
            if is_ota_viable:
                parent_window["-UPDATE_BAR-"].update(f"Downloading v{latest_version}...")
                threading.Thread(
                    target=download_update_task,
                    args=(parent_window, binary_url, dest_path),
                    daemon=True
                ).start()
                result = True
            else:
                webbrowser.open(browser_url)
                result = False
            break

    window.close()
    return result


def show_feedback_window() -> None:
    """Display the Feedback Hub modal window and handle submission."""
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

            threading.Thread(
                target=submit_feedback_task,
                args=(fb_window, payload),
                daemon=True
            ).start()

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
    """
    Display a technical modal for critical unhandled exceptions.

    Args:
        error_msg: The exception message.
        stack_trace: Full traceback string.
    """
    layout = [
        [sg.Text("⚠️ Critical Error Detected", font=("Any", 14, "bold"), text_color="red")],
        [sg.Text("The application has encountered an unexpected problem.")],

        # Technical details section
        [sg.Multiline(f"Error: {error_msg}\n\n{stack_trace}",
                      size=(75, 10),
                      font=("Courier", 8),
                      disabled=True,
                      background_color="#F0F0F0")],

        [sg.HorizontalSeparator()],

        # User context section
        [sg.Text("What were you doing when this happened? (Optional):", font=("Any", 9, "bold"))],
        [sg.Multiline(key="-CRASH_COMMENT-", size=(75, 3),
                      tooltip="E.g.: I was loading a profile while the scan was running.")],

        [sg.Text("Note: Technical logs and system info will be attached to the report.",
                 font=("Any", 7), text_color="gray")],

        [
            sg.Button("Copy to Clipboard", key="-COPY_ERR-"),
            sg.Button("Send Error Report", key="-SEND_REPORT-", button_color="green"),
            sg.Push(),
            sg.Button("Close", key="-EXIT_ERR-", button_color="red")
        ],
        [sg.Text("", key="-REPORT_STATUS-", visible=False, font=("Any", 9, "bold"))]
    ]

    window = sg.Window("Crash Reporter", layout, modal=True, finalize=True)

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "-EXIT_ERR-"):
            break

        if event == "-COPY_ERR-":
            sg.clipboard_set(f"Error: {error_msg}\n\n{stack_trace}")
            sg.popup_quick_message("Copied to clipboard!")

        if event == "-SEND_REPORT-":
            window["-SEND_REPORT-"].update(disabled=True)
            window["-REPORT_STATUS-"].update("Sending report...", visible=True, text_color="blue")

            payload = {
                "error": error_msg,
                "stack_trace": stack_trace,
                "user_comment": values.get("-CRASH_COMMENT-", ""),
                "app_version": cfg.CURRENT_CONFIG_VERSION,
                "os": platform.system(),
                "logs": get_recent_logs(150)
            }

            threading.Thread(
                target=submit_error_report_task,
                args=(window, payload),
                daemon=True
            ).start()

        if event == "-ERROR-REPORT-SUBMITTED-":
            success, msg = values[event]
            if success:
                window["-REPORT_STATUS-"].update("Report sent! Thank you.", text_color="green")
                sg.popup("Error report submitted successfully. We will investigate this issue.")
                break
            else:
                window["-REPORT_STATUS-"].update("Failed to send report.", text_color="red")
                window["-SEND_REPORT-"].update(disabled=False)
                sg.popup_error(f"Error report failed:\n{msg}")

    window.close()


def show_results_window(result: PipelineResult) -> None:
    """
    Show detailed pipeline execution summary and metrics.

    Args:
        result: The PipelineResult object from the core engine.
    """
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
         sg.Text(f"{summary.get('skipped', 0)}", text_color="orange")],
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
            open_file_explorer(result.final_output_path)
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
# Configuration Sync Helpers
# -----------------------------------------------------------------------------
def update_config_from_gui(config: Dict[str, Any], values: Dict[str, Any]) -> None:
    """
    Synchronize UI values back to the config dictionary.
    Reads values from PySimpleGUI input dict and updates the config object reference.
    """
    for k in ["input_path", "output_base_dir", "output_subdir_name", "output_prefix", "target_model"]:
        config[k] = values.get(k)

    bool_keys = [
        "process_modules", "process_tests", "process_resources", "generate_tree",
        "create_individual_files", "create_unified_file", "show_functions",
        "show_classes", "show_methods", "print_tree", "save_error_log",
        "respect_gitignore", "enable_sanitizer", "mask_user_paths", "minify_output"
    ]
    for k in bool_keys:
        config[k] = bool(values.get(k))

    config["extensions"] = parse_list_from_string(values.get("extensions", ""))
    config["include_patterns"] = parse_list_from_string(values.get("include_patterns", ""))
    config["exclude_patterns"] = parse_list_from_string(values.get("exclude_patterns", ""))


def populate_gui_from_config(window: sg.Window, config: Dict[str, Any]) -> None:
    """
    Populate UI fields from a config dictionary.

    Args:
        window: The main window to update.
        config: The configuration dictionary to read from.
    """
    keys = ["input_path", "output_base_dir", "output_subdir_name", "output_prefix",
            "process_modules", "process_tests", "generate_tree", "create_individual_files",
            "create_unified_file", "show_functions", "show_classes", "show_methods",
            "print_tree", "save_error_log", "respect_gitignore",
            "enable_sanitizer", "mask_user_paths", "minify_output"]

    for k in keys:
        if k in window.AllKeysDict:
            window[k].update(config.get(k))

    window["process_resources"].update(config.get("process_resources", False))
    window["target_model"].update(config.get("target_model", "GPT-4o / GPT-5"))
    window["extensions"].update(",".join(config.get("extensions", [])))
    window["include_patterns"].update(",".join(config.get("include_patterns", [])))
    window["exclude_patterns"].update(",".join(config.get("exclude_patterns", [])))

    if "-STACK-" in window.AllKeysDict:
        window["-STACK-"].update(value="-- Select --")

    tree_enabled = bool(config.get("generate_tree", False))
    for k in ["show_functions", "show_classes", "show_methods"]:
        window[k].update(disabled=not tree_enabled)


def toggle_ui_state(window: sg.Window, is_disabled: bool) -> None:
    """
    Enable or disable interactive elements during long operations.

    Args:
        window: The GUI window.
        is_disabled: True to disable buttons, False to enable.
    """
    keys = ["btn_process", "btn_simulate", "btn_reset", "btn_browse_in", "btn_browse_out",
            "btn_load_profile", "btn_save_profile", "btn_del_profile", "btn_feedback"]
    for key in keys:
        if key in window.AllKeysDict:
            window[key].update(disabled=is_disabled)