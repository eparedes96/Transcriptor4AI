from __future__ import annotations

from transcriptor4ai.interface.gui.handlers import logger, _show_update_prompt, show_feedback_window, show_crash_modal, \
    _show_results_window, update_config_from_gui, populate_gui_from_config, _toggle_ui_state
from transcriptor4ai.interface.gui.threads import _run_pipeline_thread, _check_updates_thread

"""
Graphical User Interface (GUI) for transcriptor4ai.

Implemented using PySimpleGUI. Manages user interactions, threaded 
pipeline execution, persistent configuration, and community feedback.
Ensures semantic layout for AST options and update lifecycle management.
Includes a pro-active Smart Error Reporter for critical failure analysis.
Includes integrated Security Sanitizer, Path Masking, and Minification.
"""

import os
import platform
import subprocess
import threading
import traceback
import webbrowser
from typing import Any, Dict

import PySimpleGUI as sg

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra.logging import (
    configure_logging,
    LoggingConfig,
    get_default_gui_log_path
)
from transcriptor4ai.core.pipeline.engine import PipelineResult
from transcriptor4ai.utils.i18n import i18n


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

    update_metadata: Dict[str, Any] = {"ready": False, "path": "", "sha256": None}

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

    # Content selection layout with hierarchical visual grouping
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
        ],
        [
            sg.Text("      └─ AST symbols:", font=("Any", 8)),
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
        [
            sg.Checkbox(i18n.t("gui.checkboxes.gitignore"), key="respect_gitignore",
                        default=config.get("respect_gitignore", True)),
            sg.Checkbox("Sanitize Secrets", key="enable_sanitizer", default=config.get("enable_sanitizer", True)),
            sg.Checkbox("Mask Paths", key="mask_user_paths", default=config.get("mask_user_paths", True)),
            sg.Checkbox("Minify", key="minify_output", default=config.get("minify_output", False)),
            sg.Checkbox(i18n.t("gui.checkboxes.log_err"), key="save_error_log", default=config["save_error_log"])
        ],
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

    populate_gui_from_config(window, config)

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

            # --- OTA Update Execution ---
            if update_metadata["ready"]:
                try:
                    import sys
                    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
                    updater_script = os.path.join(base_path, "updater.py")

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
            break

        # --- Update Lifecycle Events ---
        if event == "Check for Updates":
            logger.info("Manual update check triggered.")
            window["-UPDATE_BAR-"].update("Checking...")
            threading.Thread(target=_check_updates_thread, args=(window, True), daemon=True).start()

        if event == "-UPDATE-FINISHED-":
            res, is_manual = values[event]
            if res.get("has_update"):
                latest = res.get('latest_version')
                binary_url = res.get("binary_url")
                browser_url = res.get("download_url")

                dest = ""
                if binary_url:
                    temp_dir = paths.get_user_data_dir()
                    dest = os.path.join(temp_dir, "tmp", f"transcriptor4ai_v{latest}.exe")
                    os.makedirs(os.path.dirname(dest), exist_ok=True)

                if _show_update_prompt(window, latest, res.get('changelog', ""), binary_url, dest, browser_url):
                    update_metadata.update({"path": dest, "sha256": res.get("sha256"), "ready": False})
            else:
                if is_manual:
                    logger.info("Update check: Already up to date.")
                    window["-UPDATE_BAR-"].update("Up to date.")
                    sg.popup(f"Transcriptor4AI is up to date (v{cfg.CURRENT_CONFIG_VERSION}).")

        if event == "-DOWNLOAD-PROGRESS-":
            percent = values[event]
            window["-UPDATE_BAR-"].update(f"Downloading: {percent:.1f}%")

        if event == "-DOWNLOAD-DONE-":
            success, msg = values[event]
            if success:
                update_metadata["ready"] = True
                window["-UPDATE_BAR-"].update("Update ready. Restart to apply.", text_color="green")
                sg.popup("Download complete! The update will be applied automatically when you close the application.")
            else:
                window["-UPDATE_BAR-"].update("Download failed.", text_color="red")
                if sg.popup_yes_no(f"Update download failed: {msg}\n\nWould you like to open the browser instead?") == "Yes":
                    webbrowser.open(browser_url or "https://github.com/eparedes96/Transcriptor4AI/releases")

        # --- Other Events ---
        if event in ("btn_feedback", "Send Feedback"):
            show_feedback_window()

        if event in ("btn_reset", "Reset Config"):
            logger.info("Configuration reset triggered.")
            config = cfg.get_default_config()
            populate_gui_from_config(window, config)
            sg.popup(i18n.t("gui.status.reset"))

        if event == "btn_load_profile":
            sel_profile = values.get("-PROFILE_LIST-")
            if sel_profile and sel_profile in app_state.get("saved_profiles", {}):
                logger.info(f"Loading profile: {sel_profile}")
                prof_data = app_state["saved_profiles"][sel_profile]
                temp_conf = cfg.get_default_config()
                temp_conf.update(prof_data)
                populate_gui_from_config(window, temp_conf)
                config.update(temp_conf)
                sg.popup(f"Profile '{sel_profile}' loaded!")
            else:
                sg.popup_error(i18n.t("gui.profiles.error_select"))

        if event == "btn_save_profile":
            name = sg.popup_get_text(i18n.t("gui.profiles.prompt_name"), title=i18n.t("gui.profiles.save"))
            if name:
                name = name.strip()
                if name in app_state["saved_profiles"]:
                    if sg.popup_yes_no(i18n.t("gui.profiles.confirm_overwrite_msg", name=name)) != "Yes":
                        continue
                update_config_from_gui(config, values)
                app_state["saved_profiles"][name] = config.copy()
                cfg.save_app_state(app_state)
                profile_names = sorted(list(app_state["saved_profiles"].keys()))
                window["-PROFILE_LIST-"].update(values=profile_names, value=name)
                sg.popup(i18n.t("gui.profiles.saved", name=name))

        if event == "btn_del_profile":
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

        # --- Standard Events ---
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
            if folder: window["input_path"].update(folder)

        if event == "btn_browse_out":
            folder = sg.popup_get_folder("Select Output", default_path=values["output_base_dir"])
            if folder: window["output_base_dir"].update(folder)

        if event in ("btn_process", "btn_simulate"):
            is_sim = (event == "btn_simulate")
            update_config_from_gui(config, values)
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
                show_crash_modal(str(res), traceback.format_exc())

    window.close()


if __name__ == "__main__":
    main()