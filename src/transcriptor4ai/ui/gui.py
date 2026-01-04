from __future__ import annotations

import logging
import os
import threading
import traceback
from typing import Any, Dict, Union

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
def actualizar_config_desde_gui(config: Dict[str, Any], values: Dict[str, Any]) -> None:
    """Update the config dictionary with values from the GUI window."""
    config["input_path"] = values["input_path"]
    config["output_base_dir"] = values["output_base_dir"]
    config["output_subdir_name"] = values["output_subdir_name"]
    config["output_prefix"] = values["output_prefix"]

    if values.get("modo_todo"):
        config["processing_mode"] = "todo"
    elif values.get("modo_modulos"):
        config["processing_mode"] = "solo_modulos"
    elif values.get("modo_tests"):
        config["processing_mode"] = "solo_tests"

    config["extensiones"] = values.get("extensiones", "")
    config["include_patterns"] = values.get("include_patterns", "")
    config["exclude_patterns"] = values.get("exclude_patterns", "")

    config["show_functions"] = bool(values.get("show_functions"))
    config["show_classes"] = bool(values.get("show_classes"))
    config["show_methods"] = bool(values.get("show_methods"))

    config["generate_tree"] = bool(values.get("generate_tree"))
    config["print_tree"] = bool(values.get("print_tree"))
    config["save_error_log"] = bool(values.get("save_error_log"))


def volcar_config_a_gui(window: sg.Window, config: Dict[str, Any]) -> None:
    """Populate the GUI fields with values from the config dictionary."""
    window["input_path"].update(config["input_path"])
    window["output_base_dir"].update(config["output_base_dir"])
    window["output_subdir_name"].update(config["output_subdir_name"])
    window["output_prefix"].update(config["output_prefix"])

    window["modo_todo"].update(config["processing_mode"] == "todo")
    window["modo_modulos"].update(config["processing_mode"] == "solo_modulos")
    window["modo_tests"].update(config["processing_mode"] == "solo_tests")

    exts = config["extensiones"] if isinstance(config["extensiones"], list) else []
    incl = config["include_patterns"] if isinstance(config["include_patterns"], list) else []
    excl = config["exclude_patterns"] if isinstance(config["exclude_patterns"], list) else []

    window["extensiones"].update(",".join(exts))
    window["include_patterns"].update(",".join(incl))
    window["exclude_patterns"].update(",".join(excl))

    window["show_functions"].update(config["show_functions"])
    window["show_classes"].update(config["show_classes"])
    window["show_methods"].update(config["show_methods"])

    window["generate_tree"].update(config["generate_tree"])
    window["print_tree"].update(config["print_tree"])
    window["save_error_log"].update(config["save_error_log"])


def _format_summary(res: PipelineResult) -> str:
    """Format the pipeline result into a human-readable string for the popup."""
    if not res.ok:
        return i18n.t("gui.popups.error_process", error=res.error)

    # Extract summary data safely
    summary = res.resumen or {}
    dry_run = summary.get("dry_run", False)

    lines = []
    if dry_run:
        lines.append(i18n.t("gui.popups.dry_run_title"))
        lines.append(i18n.t("gui.popups.dry_run_msg", files=summary.get('will_generate', [])))
    else:
        lines.append(i18n.t("gui.popups.success_title"))
        lines.append(i18n.t("gui.popups.output_path", path=res.salida_real))
        lines.append("-" * 30)
        lines.append(i18n.t("gui.popups.stats",
                            proc=summary.get('procesados', 0),
                            skip=summary.get('omitidos', 0),
                            err=summary.get('errores', 0)))

        # Details about generated files
        generados = summary.get("generados", {})
        if generados:
            lines.append(i18n.t("gui.popups.generated_files"))
            if generados.get("tests"): lines.append(f" - Tests")
            if generados.get("modulos"): lines.append(f" - Modules")
            if generados.get("errores"): lines.append(f" - Error Log")

        arbol_info = summary.get("arbol", {})
        if arbol_info.get("generado"):
            lines.append(f" - Tree ({arbol_info.get('lineas')} lines)")

    return "\n".join(lines)


def _toggle_ui_state(window: sg.Window, disabled: bool) -> None:
    """Helper to enable/disable buttons during processing."""
    # Use explicit keys for reliable access regardless of language
    for key in ["btn_process", "btn_save", "btn_reset", "btn_explorar_in", "btn_examinar_out"]:
        window[key].update(disabled=disabled)


# -----------------------------------------------------------------------------
# Main GUI Entry Point
# -----------------------------------------------------------------------------
def main() -> None:
    # 1. Setup Logging
    log_path = get_default_gui_log_path()
    log_conf = LoggingConfig(level="INFO", console=True, log_file=log_path)
    configure_logging(log_conf)

    logger.info("GUI starting...")
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
    layout = [
        # --- Input ---
        [sg.Text(i18n.t("gui.sections.input"))],
        [
            sg.Input(default_text=config["input_path"], size=(70, 1), key="input_path",
                     tooltip=i18n.t("gui.tooltips.input")),
            sg.Button(i18n.t("gui.buttons.explore"), key="btn_explorar_in"),
        ],

        # --- Output ---
        [sg.Text(i18n.t("gui.sections.output"))],
        [
            sg.Input(default_text=config["output_base_dir"], size=(70, 1), key="output_base_dir",
                     tooltip=i18n.t("gui.tooltips.output")),
            sg.Button(i18n.t("gui.buttons.examine"), key="btn_examinar_out"),
        ],
        [
            sg.Text(i18n.t("gui.sections.sub_output")),
            sg.Input(default_text=config["output_subdir_name"], size=(20, 1), key="output_subdir_name",
                     tooltip=i18n.t("gui.tooltips.subdir")),
            sg.Text(i18n.t("gui.sections.prefix")),
            sg.Input(default_text=config["output_prefix"], size=(20, 1), key="output_prefix",
                     tooltip=i18n.t("gui.tooltips.prefix")),
        ],

        # --- Mode ---
        [sg.Text(i18n.t("gui.sections.mode"))],
        [
            sg.Radio(i18n.t("gui.radios.all"), "RADIO1", key="modo_todo",
                     default=(config["processing_mode"] == "todo")),
            sg.Radio(i18n.t("gui.radios.modules"), "RADIO1", key="modo_modulos",
                     default=(config["processing_mode"] == "solo_modulos")),
            sg.Radio(i18n.t("gui.radios.tests"), "RADIO1", key="modo_tests",
                     default=(config["processing_mode"] == "solo_tests")),
        ],

        # --- Filters ---
        [sg.Text(i18n.t("gui.labels.extensions")),
         sg.Input(",".join(config["extensiones"]), size=(60, 1), key="extensiones",
                  tooltip=i18n.t("gui.tooltips.ext"))],
        [sg.Text(i18n.t("gui.labels.include")),
         sg.Input(",".join(config["include_patterns"]), size=(60, 1), key="include_patterns",
                  tooltip=i18n.t("gui.tooltips.inc"))],
        [sg.Text(i18n.t("gui.labels.exclude")),
         sg.Input(",".join(config["exclude_patterns"]), size=(60, 1), key="exclude_patterns",
                  tooltip=i18n.t("gui.tooltips.exc"))],

        # --- Tree Options ---
        [
            sg.Checkbox(i18n.t("gui.checkboxes.func"), key="show_functions", default=config["show_functions"]),
            sg.Checkbox(i18n.t("gui.checkboxes.cls"), key="show_classes", default=config["show_classes"]),
            sg.Checkbox(i18n.t("gui.checkboxes.meth"), key="show_methods", default=config["show_methods"]),
        ],
        [
            sg.Checkbox(i18n.t("gui.checkboxes.gen_tree"), key="generate_tree", default=config["generate_tree"]),
            sg.Checkbox(i18n.t("gui.checkboxes.print_tree"), key="print_tree", default=config["print_tree"]),
        ],
        [
            sg.Checkbox(i18n.t("gui.checkboxes.log_err"), key="save_error_log", default=config["save_error_log"]),
            sg.Checkbox(i18n.t("gui.checkboxes.dry_run"), key="dry_run", default=False, text_color="blue",
                        tooltip=i18n.t("gui.tooltips.dry_run")),
        ],

        # --- Status Indicator (Hidden by default) ---
        [sg.Text(i18n.t("gui.status.processing"), key="-STATUS-", text_color="blue", visible=False,
                 font=("Any", 10, "bold"))],

        # --- Actions ---
        [
            sg.Button(i18n.t("gui.buttons.process"), key="btn_process", button_color=("white", "green")),
            sg.Button(i18n.t("gui.buttons.save"), key="btn_save"),
            sg.Button(i18n.t("gui.buttons.reset"), key="btn_reset"),
            sg.Button(i18n.t("gui.buttons.exit"), key="btn_exit", button_color=("white", "red")),
        ],
    ]

    window = sg.Window(i18n.t("app.name"), layout, finalize=True)

    # 4. Event Loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "btn_exit"):
            break

        # --- File Browsing ---
        if event == "btn_explorar_in":
            initial = paths.normalize_path(values.get("input_path", ""), os.getcwd())
            folder = sg.popup_get_folder(i18n.t("gui.tooltips.input"), default_path=initial)
            if folder:
                window["input_path"].update(folder)
                curr_out = (values.get("output_base_dir") or "").strip()
                if not curr_out or os.path.abspath(curr_out) == os.path.abspath(initial):
                    window["output_base_dir"].update(folder)

        if event == "btn_examinar_out":
            initial = paths.normalize_path(values.get("output_base_dir", ""), values.get("input_path", ""))
            folder = sg.popup_get_folder(i18n.t("gui.tooltips.output"), default_path=initial)
            if folder:
                window["output_base_dir"].update(folder)

        # --- Configuration Actions ---
        if event == "btn_save":
            try:
                actualizar_config_desde_gui(config, values)
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
            volcar_config_a_gui(window, config)
            sg.popup(i18n.t("gui.status.reset"))
            logger.info("Configuration reset to defaults.")

        # --- PROCESS ACTION (Prepare & Thread Start) ---
        if event == "btn_process":
            try:
                actualizar_config_desde_gui(config, values)

                # 1. Validation (Gatekeeper)
                clean_conf, warnings = validate_config(config, strict=False)
                if warnings:
                    logger.warning(f"Config warnings: {warnings}")

                # 2. Path Checks
                input_path = paths.normalize_path(clean_conf["input_path"], os.getcwd())
                output_base_dir = paths.normalize_path(clean_conf["output_base_dir"], input_path)
                output_subdir_name = clean_conf["output_subdir_name"]

                if not os.path.exists(input_path):
                    sg.popup_error(i18n.t("gui.popups.error_path", path=input_path))
                    continue
                if not os.path.isdir(input_path):
                    sg.popup_error(i18n.t("gui.popups.error_dir", path=input_path))
                    continue

                # 3. Overwrite & Dry Run Checks (Must happen in Main Thread due to Popups)
                is_dry_run = bool(values.get("dry_run"))
                should_overwrite = False

                if not is_dry_run:
                    salida_real = paths.get_real_output_path(output_base_dir, output_subdir_name)
                    nombres = paths.get_destination_filenames(
                        clean_conf["output_prefix"],
                        clean_conf["processing_mode"],
                        clean_conf["generate_tree"]
                    )
                    existentes = paths.check_existing_output_files(salida_real, nombres)

                    if existentes:
                        msg = i18n.t("gui.popups.overwrite_msg", files="\n".join(existentes))
                        resp = sg.popup_yes_no(msg, title=i18n.t("gui.popups.overwrite_title"), icon="warning")
                        if resp != "Yes":
                            logger.info("Process cancelled by user (overwrite check).")
                            continue
                        should_overwrite = True

                # 4. Start Thread (Freeze UI)
                _toggle_ui_state(window, disabled=True)
                window["-STATUS-"].update(visible=True)

                thread_conf = clean_conf.copy()

                logger.info(f"Starting pipeline thread (DryRun={is_dry_run})...")
                threading.Thread(
                    target=_run_pipeline_thread,
                    args=(window, thread_conf, should_overwrite, is_dry_run),
                    daemon=True
                ).start()

            except Exception as e:
                tb = traceback.format_exc(limit=5)
                logger.critical(f"Error starting pipeline: {e}\n{tb}")
                sg.popup_error(i18n.t("gui.popups.error_process", error=e))

        # --- THREAD COMPLETION (Receive Result) ---
        if event == "-THREAD-DONE-":
            # 1. Restore UI
            window["-STATUS-"].update(visible=False)
            _toggle_ui_state(window, disabled=False)

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