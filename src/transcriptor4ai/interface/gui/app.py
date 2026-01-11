from __future__ import annotations

"""
Main Entry Point for the Graphical User Interface.

This module orchestrates the application lifecycle:
1. Initialization (Logging, State Load).
2. UI Construction (via layouts.py).
3. Event Loop Processing (delegating to handlers and threads).
4. Update Lifecycle Management.
"""

import logging
import os
import platform
import subprocess
import sys
import threading
import traceback
import webbrowser
from typing import Any, Dict

import PySimpleGUI as sg

from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra import paths
from transcriptor4ai.infra.logging import (
    configure_logging,
    LoggingConfig,
    get_default_gui_log_path
)
from transcriptor4ai.utils.i18n import i18n

# Import MVC components
from transcriptor4ai.interface.gui import layouts, handlers, threads

logger = logging.getLogger(__name__)


def main() -> None:
    """Main GUI Application loop."""
    # 1. System Initialization
    log_path = get_default_gui_log_path()
    configure_logging(LoggingConfig(level="INFO", console=True, log_file=log_path))
    logger.info(f"GUI Starting - Version {cfg.CURRENT_CONFIG_VERSION}")

    # 2. State Loading
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

    # Local state for OTA updates
    update_metadata: Dict[str, Any] = {"ready": False, "path": "", "sha256": None}

    # 3. View Construction
    window = layouts.create_main_window(profile_names, config)

    # 4. Background Tasks Initialization
    if app_state["app_settings"].get("auto_check_updates"):
        threading.Thread(
            target=threads.check_updates_task,
            args=(window, False),
            daemon=True
        ).start()

    # 5. Main Event Loop
    while True:
        event, values = window.read()

        # --- Exit & Cleanup ---
        if event in (sg.WIN_CLOSED, "btn_exit", "Exit"):
            if values:
                handlers.update_config_from_gui(config, values)
                app_state["last_session"] = config
                cfg.save_app_state(app_state)

            _handle_ota_restart(update_metadata)
            break

        # --- Update Lifecycle Events ---
        if event == "Check for Updates":
            logger.info("Manual update check triggered.")
            window["-UPDATE_BAR-"].update("Checking...")
            threading.Thread(
                target=threads.check_updates_task,
                args=(window, True),
                daemon=True
            ).start()

        if event == "-UPDATE-FINISHED-":
            _handle_update_finished(window, values[event], update_metadata)

        if event == "-DOWNLOAD-PROGRESS-":
            percent = values[event]
            window["-UPDATE_BAR-"].update(f"Downloading: {percent:.1f}%")

        if event == "-DOWNLOAD-DONE-":
            _handle_download_done(window, values[event], update_metadata)

        # --- User Interaction Events (Delegated to Handlers) ---
        if event in ("btn_feedback", "Send Feedback"):
            handlers.show_feedback_window()

        if event in ("btn_reset", "Reset Config"):
            logger.info("Configuration reset triggered.")
            config = cfg.get_default_config()
            handlers.populate_gui_from_config(window, config)
            sg.popup(i18n.t("gui.status.reset"))

        if event == "btn_load_profile":
            _handle_load_profile(window, values, app_state, config)

        if event == "btn_save_profile":
            _handle_save_profile(window, values, app_state, config)

        if event == "btn_del_profile":
            _handle_delete_profile(window, values, app_state)

        # --- UI Dynamic Logic ---
        if event == "generate_tree":
            enabled = bool(values["generate_tree"])
            for k in ["show_functions", "show_classes", "show_methods"]:
                val = values[k] if enabled else False
                window[k].update(value=val, disabled=not enabled)

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

        # --- Processing Events ---
        if event in ("btn_process", "btn_simulate"):
            is_sim = (event == "btn_simulate")
            handlers.update_config_from_gui(config, values)

            if not os.path.isdir(config["input_path"]):
                sg.popup_error("Invalid input directory.")
                continue

            handlers.toggle_ui_state(window, True)
            window["-STATUS-"].update(
                "SIMULATING..." if is_sim else "PROCESSING...",
                visible=True,
                text_color="#007ACC" if is_sim else "blue"
            )

            threading.Thread(
                target=threads.run_pipeline_task,
                args=(window, config, True, is_sim),
                daemon=True
            ).start()

        if event == "-THREAD-DONE-":
            handlers.toggle_ui_state(window, False)
            window["-STATUS-"].update(visible=False)
            res = values[event]

            if isinstance(res, PipelineResult):
                if res.ok:
                    handlers.show_results_window(res)
                else:
                    sg.popup_error(f"Error: {res.error}")
            elif isinstance(res, Exception):
                handlers.show_crash_modal(str(res), traceback.format_exc())

    window.close()


# -----------------------------------------------------------------------------
# Private Event Helpers
# -----------------------------------------------------------------------------
def _handle_load_profile(window, values, app_state, config):
    sel_profile = values.get("-PROFILE_LIST-")
    if sel_profile and sel_profile in app_state.get("saved_profiles", {}):
        logger.info(f"Loading profile: {sel_profile}")
        prof_data = app_state["saved_profiles"][sel_profile]
        temp_conf = cfg.get_default_config()
        temp_conf.update(prof_data)
        handlers.populate_gui_from_config(window, temp_conf)
        config.update(temp_conf)
        sg.popup(f"Profile '{sel_profile}' loaded!")
    else:
        sg.popup_error(i18n.t("gui.profiles.error_select"))


def _handle_save_profile(window, values, app_state, config):
    name = sg.popup_get_text(i18n.t("gui.profiles.prompt_name"), title=i18n.t("gui.profiles.save"))
    if name:
        name = name.strip()
        if name in app_state["saved_profiles"]:
            msg = i18n.t("gui.profiles.confirm_overwrite_msg", name=name)
            if sg.popup_yes_no(msg) != "Yes":
                return
        handlers.update_config_from_gui(config, values)
        app_state["saved_profiles"][name] = config.copy()
        cfg.save_app_state(app_state)
        profile_names = sorted(list(app_state["saved_profiles"].keys()))
        window["-PROFILE_LIST-"].update(values=profile_names, value=name)
        sg.popup(i18n.t("gui.profiles.saved", name=name))


def _handle_delete_profile(window, values, app_state):
    sel_profile = values.get("-PROFILE_LIST-")
    if sel_profile and sel_profile in app_state["saved_profiles"]:
        if sg.popup_yes_no(i18n.t("gui.profiles.confirm_delete", name=sel_profile)) == "Yes":
            del app_state["saved_profiles"][sel_profile]
            cfg.save_app_state(app_state)
            profile_names = sorted(list(app_state["saved_profiles"].keys()))
            window["-PROFILE_LIST-"].update(values=profile_names, value="")
            sg.popup(i18n.t("gui.profiles.deleted"))
    else:
        sg.popup_error(i18n.t("gui.profiles.error_select"))


def _handle_update_finished(window, payload, update_metadata):
    res, is_manual = payload
    if res.get("has_update"):
        latest = res.get('latest_version')
        binary_url = res.get("binary_url")
        browser_url = res.get("download_url")

        dest = ""
        if binary_url:
            temp_dir = paths.get_user_data_dir()
            dest = os.path.join(temp_dir, "tmp", f"transcriptor4ai_v{latest}.exe")
            os.makedirs(os.path.dirname(dest), exist_ok=True)

        should_download = handlers.show_update_prompt_modal(
            window, latest, res.get('changelog', ""), binary_url, dest, browser_url
        )

        if should_download:
            update_metadata.update({"path": dest, "sha256": res.get("sha256"), "ready": False})
    else:
        if is_manual:
            logger.info("Update check: Already up to date.")
            window["-UPDATE_BAR-"].update("Up to date.")
            sg.popup(f"Transcriptor4AI is up to date (v{cfg.CURRENT_CONFIG_VERSION}).")


def _handle_download_done(window, payload, update_metadata):
    success, msg = payload
    if success:
        update_metadata["ready"] = True
        window["-UPDATE_BAR-"].update("Update ready. Restart to apply.", text_color="green")
        sg.popup("Download complete! The update will be applied automatically when you close the application.")
    else:
        window["-UPDATE_BAR-"].update("Download failed.", text_color="red")
        if sg.popup_yes_no(f"Update download failed: {msg}\n\nOpen GitHub releases?") == "Yes":
            webbrowser.open("https://github.com/eparedes96/Transcriptor4AI/releases")


def _handle_ota_restart(update_metadata):
    if update_metadata["ready"]:
        try:
            base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
            updater_script = os.path.join(base_path, "updater.py")
            if not os.path.exists(updater_script):
                updater_script = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "..", "scripts", "updater.py"
                ))

            if os.path.exists(updater_script):
                cmd = [
                    sys.executable, updater_script,
                    "--pid", str(os.getpid()),
                    "--old", sys.executable,
                    "--new", update_metadata["path"]
                ]
                if update_metadata["sha256"]:
                    cmd += ["--sha256", update_metadata["sha256"]]

                subprocess.Popen(
                    cmd,
                    creationflags=subprocess.CREATE_NEW_CONSOLE if platform.system() == "Windows" else 0,
                    start_new_session=True
                )
        except Exception as e:
            logger.error(f"Failed to launch OTA updater: {e}")


if __name__ == "__main__":
    main()