from __future__ import annotations

"""
Graphical User Interface (GUI) for transcriptor4ai.

Implemented using PySimpleGUI. Manages user interactions, threaded 
pipeline execution, and persistent configuration.
Refactored for v1.1.0 (Granular Selection & Flexible Output).
"""

import logging
import os
import threading
import traceback
from typing import Any, Dict, List

import PySimpleGUI as sg

from transcriptor4ai import config as cfg
from transcriptor4ai import paths
from transcriptor4ai.logging import configure_logging, LoggingConfig, get_default_gui_log_path
from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.pipeline import run_pipeline, PipelineResult
from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Threading Helper
# -----------------------------------------------------------------------------
def _run_pipeline_thread(
        window: sg.Window,
        config: Dict[str, Any],
        overwrite: bool,
        dry_run: bool
) -> None:
    """
    Wrapper to execute the pipeline in a separate thread.
    Sends the result back to the main GUI thread via window event.
    """
    try:
        result = run_pipeline(config, overwrite=overwrite, dry_run=dry_run)
        window.write_event_value("-THREAD-DONE-", result)
    except Exception as e:
        logger.critical(f"Critical failure in pipeline thread: {e}", exc_info=True)
        window.write_event_value("-THREAD-DONE-", e)


# -----------------------------------------------------------------------------
# GUI: Config Helpers
# -----------------------------------------------------------------------------
def update_config_from_gui(config: Dict[str, Any], values: Dict[str, Any]) -> None:
    """Update the config dictionary with values from the GUI window."""
    config["input_path"] = values["input_path"]
    config["output_base_dir"] = values["output_base_dir"]
    config["output_subdir_name"] = values["output_subdir_name"]
    config["output_prefix"] = values["output_prefix"]

    # Content Selection
    config["process_modules"] = bool(values.get("process_modules"))
    config["process_tests"] = bool(values.get("process_tests"))
    config["generate_tree"] = bool(values.get("generate_tree"))

    # Output Format
    config["create_individual_files"] = bool(values.get("create_individual_files"))
    config["create_unified_file"] = bool(values.get("create_unified_file"))

    # Filters
    config["extensions"] = values.get("extensions", "")
    config["include_patterns"] = values.get("include_patterns", "")
    config["exclude_patterns"] = values.get("exclude_patterns", "")

    # AST Options
    config["show_functions"] = bool(values.get("show_functions"))
    config["show_classes"] = bool(values.get("show_classes"))
    config["show_methods"] = bool(values.get("show_methods"))
    config["print_tree"] = bool(values.get("print_tree"))

    # Logging
    config["save_error_log"] = bool(values.get("save_error_log"))


def populate_gui_from_config(window: sg.Window, config: Dict[str, Any]) -> None:
    """Populate the GUI fields with values from the config dictionary."""
    window["input_path"].update(config["input_path"])
    window["output_base_dir"].update(config["output_base_dir"])
    window["output_subdir_name"].update(config["output_subdir_name"])
    window["output_prefix"].update(config["output_prefix"])

    # Content Selection
    window["process_modules"].update(config["process_modules"])
    window["process_tests"].update(config["process_tests"])
    window["generate_tree"].update(config["generate_tree"])

    # Output Format
    window["create_individual_files"].update(config["create_individual_files"])
    window["create_unified_file"].update(config["create_unified_file"])

    # Filters
    exts = config["extensions"] if isinstance(config["extensions"], list) else []
    incl = config["include_patterns"] if isinstance(config["include_patterns"], list) else []
    excl = config["exclude_patterns"] if isinstance(config["exclude_patterns"], list) else []

    window["extensions"].update(",".join(exts))
    window["include_patterns"].update(",".join(incl))
    window["exclude_patterns"].update(",".join(excl))

    # AST & Options
    window["show_functions"].update(config["show_functions"])
    window["show_classes"].update(config["show_classes"])
    window["show_methods"].update(config["show_methods"])
    window["print_tree"].update(config["print_tree"])
    window["save_error_log"].update(config["save_error_log"])


def _format_summary(res: PipelineResult) -> str:
    """Format the pipeline result into a human-readable string for the popup."""
    if not res.ok:
        return i18n.t("gui.popups.error_process", error=res.error)

    # Standardized access to summary
    summary = res.summary or {}
    dry_run = summary.get("dry_run", False)

    lines = []
    if dry_run:
        lines.append(i18n.t("gui.popups.dry_run_title"))
        lines.append(i18n.t("gui.popups.dry_run_msg", files=summary.get('will_generate', [])))
    else:
        lines.append(i18n.t("gui.popups.success_title"))
        lines.append(i18n.t("gui.popups.output_path", path=res.final_output_path))
        lines.append("-" * 30)

        lines.append(i18n.t("gui.popups.stats",
                            proc=summary.get('processed', 0),
                            skip=summary.get('skipped', 0),
                            err=summary.get('errors', 0)))

        # Details about generated files
        gen_files = summary.get("generated_files", {})
        if gen_files:
            lines.append(i18n.t("gui.popups.generated_files"))
            for key, path in gen_files.items():
                if path:
                    lines.append(f" - {key.capitalize()}")

        tree_info = summary.get("tree", {})
        if tree_info.get("generated"):
            lines.append(f" - Tree ({tree_info.get('lines')} lines)")

    return "\n".join(lines)


def _toggle_ui_state(window: sg.Window, is_disabled: bool) -> None:
    """Helper to enable/disable buttons during processing."""
    for key in ["btn_process", "btn_simulate", "btn_save", "btn_reset", "btn_browse_in", "btn_browse_out"]:
        window[key].update(disabled=is_disabled)


# -----------------------------------------------------------------------------
# Main GUI Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    # 1. Setup Logging
    log_path = get_default_gui_log_path()
    log_conf = LoggingConfig(level="INFO", console=True, log_file=log_path)
    configure_logging(log_conf)

    logger.info("GUI starting (v1.1.0 logic)...")
    sg.theme("SystemDefault")

    # 2. Load Initial Config
    try:
        raw_config = cfg.load_config()
        config, _ = validate_config(raw_config, strict=False)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = cfg.get_default_config()

    if not config.get("output_base_dir"):
        config["output_base_dir"] = config.get("input_path") or os.getcwd()

    # 3. Define Layout

    frame_content = [
        [
            sg.Checkbox(i18n.t("gui.checkboxes.modules"), key="process_modules", default=True),
            sg.Checkbox(i18n.t("gui.checkboxes.tests"), key="process_tests", default=True),
        ],
        [
            sg.Checkbox(i18n.t("gui.checkboxes.gen_tree"), key="generate_tree", default=False),
        ],
        [
            sg.Text("    └─ AST:", font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.func"), key="show_functions", font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.cls"), key="show_classes", font=("Any", 8)),
            sg.Checkbox(i18n.t("gui.checkboxes.meth"), key="show_methods", font=("Any", 8)),
        ]
    ]

    # -- Output Format Frame --
    frame_output_format = [
        [
            sg.Checkbox(i18n.t("gui.checkboxes.individual"), key="create_individual_files", default=True,
                        tooltip="Generates separate .txt files for each component"),
            sg.Checkbox(i18n.t("gui.checkboxes.unified"), key="create_unified_file", default=True,
                        tooltip="Generates a single '_full_context.txt' file"),
        ]
    ]

    layout = [
        # --- Input ---
        [sg.Text(i18n.t("gui.sections.input"))],
        [
            sg.Input(default_text=config["input_path"], size=(70, 1), key="input_path",
                     expand_x=True, tooltip=i18n.t("gui.tooltips.input")),
            sg.Button(i18n.t("gui.buttons.explore"), key="btn_browse_in"),
        ],

        # --- Output Path ---
        [sg.Text(i18n.t("gui.sections.output"))],
        [
            sg.Input(default_text=config["output_base_dir"], size=(70, 1), key="output_base_dir",
                     expand_x=True, tooltip=i18n.t("gui.tooltips.output")),
            sg.Button(i18n.t("gui.buttons.examine"), key="btn_browse_out"),
        ],
        [
            sg.Text(i18n.t("gui.sections.sub_output")),
            sg.Input(default_text=config["output_subdir_name"], size=(20, 1), key="output_subdir_name",
                     tooltip=i18n.t("gui.tooltips.subdir")),
            sg.Text(i18n.t("gui.sections.prefix")),
            sg.Input(default_text=config["output_prefix"], size=(20, 1), key="output_prefix",
                     tooltip=i18n.t("gui.tooltips.prefix")),
        ],

        # --- New Flexible Config Sections ---
        [
            sg.Frame(i18n.t("gui.sections.content"), frame_content, expand_x=True),
        ],
        [
            sg.Frame(i18n.t("gui.sections.format"), frame_output_format, expand_x=True)
        ],

        # --- Filters ---
        [sg.Text(i18n.t("gui.labels.extensions")),
         sg.Input(",".join(config["extensions"]), size=(60, 1), key="extensions", expand_x=True)],
        [sg.Text(i18n.t("gui.labels.include")),
         sg.Input(",".join(config["include_patterns"]), size=(60, 1), key="include_patterns", expand_x=True)],
        [sg.Text(i18n.t("gui.labels.exclude")),
         sg.Input(",".join(config["exclude_patterns"]), size=(60, 1), key="exclude_patterns", expand_x=True)],

        # --- Misc ---
        [
            sg.Checkbox(i18n.t("gui.checkboxes.print_tree"), key="print_tree", default=config["print_tree"],
                        visible=False),  # Hidden but kept for logic
            sg.Checkbox(i18n.t("gui.checkboxes.log_err"), key="save_error_log", default=config["save_error_log"]),
        ],

        # --- Status Indicator ---
        [sg.Text(i18n.t("gui.status.processing"), key="-STATUS-", text_color="blue", visible=False,
                 font=("Any", 10, "bold"))],

        # --- Actions ---
        [
            sg.Button(i18n.t("gui.buttons.simulate"), key="btn_simulate", button_color=("white", "#007ACC")),
            sg.Button(i18n.t("gui.buttons.process"), key="btn_process", button_color=("white", "green")),
            sg.Push(),  # Spacer
            sg.Button(i18n.t("gui.buttons.save"), key="btn_save"),
            sg.Button(i18n.t("gui.buttons.reset"), key="btn_reset"),
            sg.Button(i18n.t("gui.buttons.exit"), key="btn_exit", button_color=("white", "red")),
        ],
    ]

    window = sg.Window(i18n.t("app.name"), layout, finalize=True, resizable=True)

    # 4. Event Loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "btn_exit"):
            break

        # --- File Browsing ---
        if event == "btn_browse_in":
            initial = paths.normalize_path(values.get("input_path", ""), os.getcwd())
            folder = sg.popup_get_folder(i18n.t("gui.tooltips.input"), default_path=initial)
            if folder:
                window["input_path"].update(folder)
                curr_out = (values.get("output_base_dir") or "").strip()
                if not curr_out or os.path.abspath(curr_out) == os.path.abspath(initial):
                    window["output_base_dir"].update(folder)

        if event == "btn_browse_out":
            initial = paths.normalize_path(values.get("output_base_dir", ""), values.get("input_path", ""))
            folder = sg.popup_get_folder(i18n.t("gui.tooltips.output"), default_path=initial)
            if folder:
                window["output_base_dir"].update(folder)

        # --- Configuration Actions ---
        if event == "btn_save":
            try:
                update_config_from_gui(config, values)
                clean_conf, _ = validate_config(config, strict=False)
                clean_conf["input_path"] = paths.normalize_path(clean_conf["input_path"], os.getcwd())
                clean_conf["output_base_dir"] = paths.normalize_path(clean_conf["output_base_dir"],
                                                                     clean_conf["input_path"])
                cfg.save_config(clean_conf)
                sg.popup(i18n.t("gui.status.success"))
                logger.info("Configuration saved by user.")
            except Exception as e:
                logger.error(f"Save config failed: {e}")
                sg.popup_error(i18n.t("gui.popups.error_save", error=e))

        if event == "btn_reset":
            config = cfg.get_default_config()
            populate_gui_from_config(window, config)
            sg.popup(i18n.t("gui.status.reset"))
            logger.info("Configuration reset to defaults.")

        # --- EXECUTION ACTIONS (SIMULATE or PROCESS) ---
        if event in ("btn_process", "btn_simulate"):
            is_simulate = (event == "btn_simulate")

            try:
                update_config_from_gui(config, values)

                # 1. Validation (Gatekeeper)
                clean_conf, warnings = validate_config(config, strict=False)
                if warnings:
                    logger.warning(f"Config warnings: {warnings}")

                # 1.1 UI specific validation
                has_content = any(
                    [clean_conf["process_modules"], clean_conf["process_tests"], clean_conf["generate_tree"]])
                has_format = any([clean_conf["create_individual_files"], clean_conf["create_unified_file"]])

                if not has_content:
                    sg.popup_error("Please select at least one content type (Modules, Tests, or Tree).")
                    continue
                if not has_format:
                    sg.popup_error("Please select at least one output format (Individual or Unified).")
                    continue

                # 2. Path Checks
                input_path = paths.normalize_path(clean_conf["input_path"], os.getcwd())
                output_base_dir = paths.normalize_path(clean_conf["output_base_dir"], input_path)
                output_subdir_name = clean_conf["output_subdir_name"]
                prefix = clean_conf["output_prefix"]

                if not os.path.exists(input_path):
                    sg.popup_error(i18n.t("gui.popups.error_path", path=input_path))
                    continue
                if not os.path.isdir(input_path):
                    sg.popup_error(i18n.t("gui.popups.error_dir", path=input_path))
                    continue

                # 3. Overwrite Check (Only if NOT Simulating)
                should_overwrite = False

                if not is_simulate:
                    salida_real = paths.get_real_output_path(output_base_dir, output_subdir_name)

                    # Manual calculation of files to check based on new config
                    nombres = []
                    if clean_conf["create_individual_files"]:
                        if clean_conf["process_modules"]: nombres.append(f"{prefix}_modules.txt")
                        if clean_conf["process_tests"]: nombres.append(f"{prefix}_tests.txt")
                        if clean_conf["generate_tree"]: nombres.append(f"{prefix}_tree.txt")

                    if clean_conf["create_unified_file"]:
                        nombres.append(f"{prefix}_full_context.txt")

                    if clean_conf["save_error_log"]:
                        nombres.append(f"{prefix}_errors.txt")

                    existentes = paths.check_existing_output_files(salida_real, nombres)

                    if existentes:
                        msg = i18n.t("gui.popups.overwrite_msg", files="\n".join(existentes))
                        resp = sg.popup_yes_no(msg, title=i18n.t("gui.popups.overwrite_title"), icon="warning")
                        if resp != "Yes":
                            logger.info("Process cancelled by user (overwrite check).")
                            continue
                        should_overwrite = True

                # 4. Start Thread
                _toggle_ui_state(window, is_disabled=True)
                window["-STATUS-"].update(visible=True)

                # Visual feedback for Simulate
                if is_simulate:
                    window["-STATUS-"].update("SIMULATING...", text_color="#007ACC")
                else:
                    window["-STATUS-"].update(i18n.t("gui.status.processing"), text_color="blue")

                thread_conf = clean_conf.copy()

                logger.info(f"Starting pipeline thread (DryRun={is_simulate})...")
                threading.Thread(
                    target=_run_pipeline_thread,
                    args=(window, thread_conf, should_overwrite, is_simulate),
                    daemon=True
                ).start()

            except Exception as e:
                tb = traceback.format_exc(limit=5)
                logger.critical(f"Error starting pipeline: {e}\n{tb}")
                sg.popup_error(i18n.t("gui.popups.error_process", error=e))

        # --- THREAD COMPLETION ---
        if event == "-THREAD-DONE-":
            # 1. Restore UI
            window["-STATUS-"].update(visible=False)
            _toggle_ui_state(window, is_disabled=False)

            # 2. Handle Result
            payload = values[event]

            if isinstance(payload, PipelineResult):
                if payload.ok:
                    logger.info("Pipeline thread finished successfully.")
                    sg.popup(_format_summary(payload), title=i18n.t("gui.popups.title_result"))
                else:
                    logger.error(f"Pipeline thread finished with error: {payload.error}")
                    sg.popup_error(i18n.t("gui.popups.error_process", error=payload.error))

            elif isinstance(payload, Exception):
                logger.critical(f"Thread crashed: {payload}")
                sg.popup_error(i18n.t("gui.popups.error_critical", error=payload))

    window.close()
    logger.info("GUI closed.")


if __name__ == "__main__":
    main()