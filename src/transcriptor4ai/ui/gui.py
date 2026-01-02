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
    config["ruta_carpetas"] = values["ruta_carpetas"]
    config["output_base_dir"] = values["output_base_dir"]
    config["output_subdir_name"] = values["output_subdir_name"]
    config["output_prefix"] = values["output_prefix"]

    if values.get("modo_todo"):
        config["modo_procesamiento"] = "todo"
    elif values.get("modo_modulos"):
        config["modo_procesamiento"] = "solo_modulos"
    elif values.get("modo_tests"):
        config["modo_procesamiento"] = "solo_tests"

    config["extensiones"] = values.get("extensiones", "")
    config["patrones_incluir"] = values.get("patrones_incluir", "")
    config["patrones_excluir"] = values.get("patrones_excluir", "")

    config["mostrar_funciones"] = bool(values.get("mostrar_funciones"))
    config["mostrar_clases"] = bool(values.get("mostrar_clases"))
    config["mostrar_metodos"] = bool(values.get("mostrar_metodos"))

    config["generar_arbol"] = bool(values.get("generar_arbol"))
    config["imprimir_arbol"] = bool(values.get("imprimir_arbol"))
    config["guardar_log_errores"] = bool(values.get("guardar_log_errores"))


def volcar_config_a_gui(window: sg.Window, config: Dict[str, Any]) -> None:
    """Populate the GUI fields with values from the config dictionary."""
    window["ruta_carpetas"].update(config["ruta_carpetas"])
    window["output_base_dir"].update(config["output_base_dir"])
    window["output_subdir_name"].update(config["output_subdir_name"])
    window["output_prefix"].update(config["output_prefix"])

    window["modo_todo"].update(config["modo_procesamiento"] == "todo")
    window["modo_modulos"].update(config["modo_procesamiento"] == "solo_modulos")
    window["modo_tests"].update(config["modo_procesamiento"] == "solo_tests")

    exts = config["extensiones"] if isinstance(config["extensiones"], list) else []
    incl = config["patrones_incluir"] if isinstance(config["patrones_incluir"], list) else []
    excl = config["patrones_excluir"] if isinstance(config["patrones_excluir"], list) else []

    window["extensiones"].update(",".join(exts))
    window["patrones_incluir"].update(",".join(incl))
    window["patrones_excluir"].update(",".join(excl))

    window["mostrar_funciones"].update(config["mostrar_funciones"])
    window["mostrar_clases"].update(config["mostrar_clases"])
    window["mostrar_metodos"].update(config["mostrar_metodos"])

    window["generar_arbol"].update(config["generar_arbol"])
    window["imprimir_arbol"].update(config["imprimir_arbol"])
    window["guardar_log_errores"].update(config["guardar_log_errores"])


def _format_summary(res: PipelineResult) -> str:
    """Format the pipeline result into a human-readable string for the popup."""
    if not res.ok:
        return f"Error:\n{res.error}"

    # Extract summary data safely
    summary = res.resumen or {}
    dry_run = summary.get("dry_run", False)

    lines = []
    if dry_run:
        lines.append("=== DRY RUN (SIMULACIÓN) COMPLETA ===")
        lines.append("No se han generado archivos.")
        lines.append(f"Se habrían generado: {summary.get('will_generate', [])}")
    else:
        lines.append("=== PROCESO COMPLETADO CON ÉXITO ===")
        lines.append(f"Salida: {res.salida_real}")
        lines.append("-" * 30)
        lines.append(f"Archivos procesados: {summary.get('procesados', 0)}")
        lines.append(f"Archivos omitidos:   {summary.get('omitidos', 0)}")
        lines.append(f"Errores de lectura:  {summary.get('errores', 0)}")

        # Details about generated files
        generados = summary.get("generados", {})
        if generados:
            lines.append("\nArchivos Generados:")
            if generados.get("tests"): lines.append(f" - Tests")
            if generados.get("modulos"): lines.append(f" - Módulos")
            if generados.get("errores"): lines.append(f" - Log de Errores")

        arbol_info = summary.get("arbol", {})
        if arbol_info.get("generado"):
            lines.append(f" - Árbol ({arbol_info.get('lineas')} líneas)")

    return "\n".join(lines)


def _toggle_ui_state(window: sg.Window, disabled: bool) -> None:
    """Helper to enable/disable buttons during processing."""
    for key in ["Procesar", "Guardar Configuración", "Resetear Configuración", "btn_explorar_in", "btn_examinar_out"]:
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
        raw_config = cfg.cargar_configuracion()
        config, _ = validate_config(raw_config, strict=False)
    except Exception as e:
        logger.error(f"Failed to load config: {e}")
        config = cfg.cargar_configuracion_por_defecto()

    if not config.get("output_base_dir"):
        config["output_base_dir"] = config.get("ruta_carpetas") or os.getcwd()

    # 3. Define Layout
    layout = [
        # --- Input ---
        [sg.Text("Ruta de la carpeta a procesar:")],
        [
            sg.Input(default_text=config["ruta_carpetas"], size=(70, 1), key="ruta_carpetas",
                     tooltip="Carpeta raíz donde está el código fuente"),
            sg.Button("Explorar", key="btn_explorar_in"),
        ],

        # --- Output ---
        [sg.Text("Ruta base de salida (se creará una subcarpeta dentro):")],
        [
            sg.Input(default_text=config["output_base_dir"], size=(70, 1), key="output_base_dir",
                     tooltip="Carpeta padre donde se guardarán los resultados"),
            sg.Button("Examinar", key="btn_examinar_out"),
        ],
        [
            sg.Text("Subcarpeta de salida:"),
            sg.Input(default_text=config["output_subdir_name"], size=(20, 1), key="output_subdir_name",
                     tooltip="Nombre de la carpeta final"),
            sg.Text("Prefijo de archivos:"),
            sg.Input(default_text=config["output_prefix"], size=(20, 1), key="output_prefix",
                     tooltip="Ej: proyecto_v1 -> proyecto_v1_modulos.txt"),
        ],

        # --- Mode ---
        [sg.Text("Modo de procesamiento:")],
        [
            sg.Radio("Todo (módulos + tests)", "RADIO1", key="modo_todo",
                     default=(config["modo_procesamiento"] == "todo")),
            sg.Radio("Solo Módulos", "RADIO1", key="modo_modulos",
                     default=(config["modo_procesamiento"] == "solo_modulos")),
            sg.Radio("Solo Tests", "RADIO1", key="modo_tests",
                     default=(config["modo_procesamiento"] == "solo_tests")),
        ],

        # --- Filters ---
        [sg.Text("Extensiones (separadas por coma):"),
         sg.Input(",".join(config["extensiones"]), size=(60, 1), key="extensiones")],
        [sg.Text("Patrones Incluir (Regex):"),
         sg.Input(",".join(config["patrones_incluir"]), size=(60, 1), key="patrones_incluir")],
        [sg.Text("Patrones Excluir (Regex):"),
         sg.Input(",".join(config["patrones_excluir"]), size=(60, 1), key="patrones_excluir")],

        # --- Tree Options ---
        [
            sg.Checkbox("Mostrar funciones", key="mostrar_funciones", default=config["mostrar_funciones"]),
            sg.Checkbox("Mostrar clases", key="mostrar_clases", default=config["mostrar_clases"]),
            sg.Checkbox("Mostrar métodos", key="mostrar_metodos", default=config["mostrar_metodos"]),
        ],
        [
            sg.Checkbox("Generar archivo de árbol", key="generar_arbol", default=config["generar_arbol"]),
            sg.Checkbox("Imprimir árbol por consola", key="imprimir_arbol", default=config["imprimir_arbol"]),
        ],
        [
            sg.Checkbox("Guardar log de errores", key="guardar_log_errores", default=config["guardar_log_errores"]),
            sg.Checkbox("Simulación (Dry Run)", key="dry_run", default=False, text_color="blue"),
        ],

        # --- Status Indicator (Hidden by default) ---
        [sg.Text("⏳ Procesando... Por favor, espere.", key="-STATUS-", text_color="blue", visible=False,
                 font=("Any", 10, "bold"))],

        # --- Actions ---
        [
            sg.Button("Procesar", button_color=("white", "green")),
            sg.Button("Guardar Configuración"),
            sg.Button("Resetear Configuración"),
            sg.Button("Salir", button_color=("white", "red")),
        ],
    ]

    window = sg.Window("Transcriptor4AI", layout, finalize=True)

    # 4. Event Loop
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Salir"):
            break

        # --- File Browsing ---
        if event == "btn_explorar_in":
            initial = paths.normalizar_dir(values.get("ruta_carpetas", ""), os.getcwd())
            folder = sg.popup_get_folder("Seleccione la carpeta a procesar", default_path=initial)
            if folder:
                window["ruta_carpetas"].update(folder)
                curr_out = (values.get("output_base_dir") or "").strip()
                if not curr_out or os.path.abspath(curr_out) == os.path.abspath(initial):
                    window["output_base_dir"].update(folder)

        if event == "btn_examinar_out":
            initial = paths.normalizar_dir(values.get("output_base_dir", ""), values.get("ruta_carpetas", ""))
            folder = sg.popup_get_folder("Seleccione la ruta base de salida", default_path=initial)
            if folder:
                window["output_base_dir"].update(folder)

        # --- Configuration Actions ---
        if event == "Guardar Configuración":
            try:
                actualizar_config_desde_gui(config, values)
                clean_conf, _ = validate_config(config, strict=False)
                clean_conf["ruta_carpetas"] = paths.normalizar_dir(clean_conf["ruta_carpetas"], os.getcwd())
                clean_conf["output_base_dir"] = paths.normalizar_dir(clean_conf["output_base_dir"],
                                                                     clean_conf["ruta_carpetas"])

                cfg.guardar_configuracion(clean_conf)
                sg.popup("Configuración guardada en config.json")
            except Exception as e:
                logger.error(f"Save config failed: {e}")
                sg.popup_error(f"No se pudo guardar configuración:\n{e}")

        if event == "Resetear Configuración":
            config = cfg.cargar_configuracion_por_defecto()
            volcar_config_a_gui(window, config)
            sg.popup("Se ha restaurado la configuración por defecto.")

        # --- PROCESS ACTION (Prepare & Thread Start) ---
        if event == "Procesar":
            try:
                actualizar_config_desde_gui(config, values)

                # 1. Validation (Gatekeeper)
                clean_conf, warnings = validate_config(config, strict=False)
                if warnings:
                    logger.warning(f"Config warnings: {warnings}")

                # 2. Path Checks
                ruta_carpetas = paths.normalizar_dir(clean_conf["ruta_carpetas"], os.getcwd())
                output_base_dir = paths.normalizar_dir(clean_conf["output_base_dir"], ruta_carpetas)
                output_subdir_name = clean_conf["output_subdir_name"]

                if not os.path.exists(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no existe:\n{ruta_carpetas}")
                    continue
                if not os.path.isdir(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no es un directorio:\n{ruta_carpetas}")
                    continue

                # 3. Overwrite & Dry Run Checks (Must happen in Main Thread due to Popups)
                is_dry_run = bool(values.get("dry_run"))
                should_overwrite = False

                if not is_dry_run:
                    salida_real = paths.ruta_salida_real(output_base_dir, output_subdir_name)
                    nombres = paths.archivos_destino(
                        clean_conf["output_prefix"],
                        clean_conf["modo_procesamiento"],
                        clean_conf["generar_arbol"]
                    )
                    existentes = paths.existen_ficheros_destino(salida_real, nombres)

                    if existentes:
                        msg = "Se van a sobrescribir estos archivos:\n\n" + "\n".join(
                            existentes) + "\n\n¿Desea continuar?"
                        resp = sg.popup_yes_no(msg, icon="warning")
                        if resp != "Yes":
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
                sg.popup_error(f"Error al iniciar el proceso:\n{e}")

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
                    sg.popup(_format_summary(payload), title="Resultado")
                else:
                    logger.error(f"Pipeline thread finished with error: {payload.error}")
                    sg.popup_error(f"Error en el proceso:\n{payload.error}")

            elif isinstance(payload, Exception):
                logger.critical(f"Thread crashed: {payload}")
                sg.popup_error(f"Error crítico en el hilo de ejecución:\n{payload}")

    window.close()
    logger.info("GUI closed.")