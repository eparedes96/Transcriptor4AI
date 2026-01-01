# main.py
# -----------------------------------------------------------------------------
# GUI (PySimpleGUI) para:
# - Transcribir código a ficheros .txt (módulos/tests)
# - Generar árbol de directorios con símbolos (funciones/clases/métodos)
# - Guardar/cargar configuración en config.json
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import json
import traceback
import PySimpleGUI as sg

from code_transcriptor import transcribir_codigo
from tree_generator import generar_arbol_directorios


# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------

CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_SUBDIR = "transcript"
DEFAULT_OUTPUT_PREFIX = "transcripcion"


# -----------------------------------------------------------------------------
# Configuración: defaults / load / save
# -----------------------------------------------------------------------------

def cargar_configuracion_por_defecto() -> dict:
    """
    Valores por defecto.

    - ruta_carpetas: carpeta a procesar (por defecto: directorio donde está main.py)
    - output_base_dir: ruta base de salida (por defecto: igual que ruta_carpetas)
    - output_subdir_name: subcarpeta que se crea dentro de output_base_dir
    - output_prefix: prefijo para los archivos generados
    """
    base = os.path.dirname(os.path.abspath(__file__))
    return {
        "ruta_carpetas": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": DEFAULT_OUTPUT_PREFIX,
        "modo_procesamiento": "todo",  # Posibles: all, only_modules, only_tests
        "extensiones": [".py"],
        "patrones_incluir": [".*"],
        "patrones_excluir": [
            r"^__init__\.py$",
            r".*\.pyc$",
            r"^(__pycache__|\.git|\.idea)$",
            r"^\."
        ],
        "mostrar_funciones": False,
        "mostrar_clases": False,
        "mostrar_metodos": False,
        "generar_arbol": False,
        "imprimir_arbol": True,
        "guardar_log_errores": True
    }


def cargar_configuracion() -> dict:
    defaults = cargar_configuracion_por_defecto()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                defaults.update(data)
        except Exception:
            # Si falla, seguimos con defaults.
            pass
    return defaults


def guardar_configuracion(config: dict) -> None:
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
    except Exception as e:
        sg.popup_error(f"No se pudo guardar {CONFIG_FILE}:\n{e}")


# -----------------------------------------------------------------------------
# Helpers de rutas / sobrescritura
# -----------------------------------------------------------------------------

def _normalizar_dir(path: str, fallback: str) -> str:
    """
    Normaliza una ruta de directorio:
    - Si está vacía, usa fallback.
    - Expande ~ y variables.
    - Convierte a absoluta.
    """
    p = (path or "").strip()
    if not p:
        p = fallback
    p = os.path.expandvars(os.path.expanduser(p))
    return os.path.abspath(p)


def _ruta_salida_real(output_base_dir: str, output_subdir_name: str) -> str:
    """
    Ruta donde se generan los ficheros:
      output_base_dir / output_subdir_name
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)


def _archivos_destino(prefix: str, modo: str, incluir_arbol: bool) -> list[str]:
    """
    Devuelve los nombres de ficheros (no rutas) que se generarían.
    """
    files: list[str] = []
    if modo in ("todo", "solo_tests"):
        files.append(f"{prefix}_tests.txt")
    if modo in ("todo", "solo_modulos"):
        files.append(f"{prefix}_modulos.txt")
    if incluir_arbol:
        files.append(f"{prefix}_arbol.txt")
    return files


def _existen_ficheros_destino(output_dir: str, names: list[str]) -> list[str]:
    """
    Devuelve la lista de ficheros (rutas completas) que YA existen.
    """
    existentes: list[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existentes.append(full)
    return existentes


# -----------------------------------------------------------------------------
# Actualización config desde GUI
# -----------------------------------------------------------------------------

def actualizar_config_desde_gui(config: dict, values: dict) -> None:
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

    config["extensiones"] = [ext.strip() for ext in (values.get("extensiones") or "").split(",") if ext.strip()]
    config["patrones_incluir"] = [pat.strip() for pat in (values.get("patrones_incluir") or "").split(",") if pat.strip()]
    config["patrones_excluir"] = [pat.strip() for pat in (values.get("patrones_excluir") or "").split(",") if pat.strip()]

    config["mostrar_funciones"] = bool(values.get("mostrar_funciones"))
    config["mostrar_clases"] = bool(values.get("mostrar_clases"))
    config["mostrar_metodos"] = bool(values.get("mostrar_metodos"))

    config["generar_arbol"] = bool(values.get("generar_arbol"))
    config["imprimir_arbol"] = bool(values.get("imprimir_arbol"))
    config["guardar_log_errores"] = bool(values.get("guardar_log_errores"))


def _volcar_config_a_gui(window: sg.Window, config: dict) -> None:
    window["ruta_carpetas"].update(config["ruta_carpetas"])
    window["output_base_dir"].update(config["output_base_dir"])
    window["output_subdir_name"].update(config["output_subdir_name"])
    window["output_prefix"].update(config["output_prefix"])

    window["modo_todo"].update(config["modo_procesamiento"] == "todo")
    window["modo_modulos"].update(config["modo_procesamiento"] == "solo_modulos")
    window["modo_tests"].update(config["modo_procesamiento"] == "solo_tests")

    window["extensiones"].update(",".join(config["extensiones"]))
    window["patrones_incluir"].update(",".join(config["patrones_incluir"]))
    window["patrones_excluir"].update(",".join(config["patrones_excluir"]))

    window["mostrar_funciones"].update(config["mostrar_funciones"])
    window["mostrar_clases"].update(config["mostrar_clases"])
    window["mostrar_metodos"].update(config["mostrar_metodos"])

    window["generar_arbol"].update(config["generar_arbol"])
    window["imprimir_arbol"].update(config["imprimir_arbol"])
    window["guardar_log_errores"].update(config["guardar_log_errores"])


# -----------------------------------------------------------------------------
# GUI principal
# -----------------------------------------------------------------------------

def main() -> None:
    sg.theme("SystemDefault")

    config = cargar_configuracion()

    if not config.get("output_base_dir"):
        config["output_base_dir"] = config.get("ruta_carpetas") or os.path.dirname(os.path.abspath(__file__))

    layout = [
        # --- Entrada ----------------------------------------------------------
        [sg.Text("Ruta de la carpeta a procesar:")],
        [
            sg.Input(default_text=config["ruta_carpetas"], size=(70, 1), key="ruta_carpetas"),
            sg.Button("Explorar", key="btn_explorar_in"),
        ],

        # --- Salida -----------------------------------------------------------
        [sg.Text("Ruta base de salida (se creará una subcarpeta dentro):")],
        [
            sg.Input(default_text=config["output_base_dir"], size=(70, 1), key="output_base_dir"),
            sg.Button("Examinar", key="btn_examinar_out"),
        ],
        [
            sg.Text("Subcarpeta de salida:"),
            sg.Input(default_text=config["output_subdir_name"], size=(20, 1), key="output_subdir_name"),
            sg.Text("Prefijo de archivos:"),
            sg.Input(default_text=config["output_prefix"], size=(20, 1), key="output_prefix"),
        ],

        # --- Modo -------------------------------------------------------------
        [sg.Text("Modo de procesamiento:")],
        [
            sg.Radio("Todo (módulos + tests)", "RADIO1", key="modo_todo", default=(config["modo_procesamiento"] == "todo")),
            sg.Radio("Solo Módulos", "RADIO1", key="modo_modulos", default=(config["modo_procesamiento"] == "solo_modulos")),
            sg.Radio("Solo Tests", "RADIO1", key="modo_tests", default=(config["modo_procesamiento"] == "solo_tests")),
        ],

        # --- Filtros ----------------------------------------------------------
        [sg.Text("Extensiones (separadas por coma):"), sg.Input(",".join(config["extensiones"]), size=(60, 1), key="extensiones")],
        [sg.Text("Patrones Incluir (separados por comas):"), sg.Input(",".join(config["patrones_incluir"]), size=(60, 1), key="patrones_incluir")],
        [sg.Text("Patrones Excluir (separados por comas):"), sg.Input(",".join(config["patrones_excluir"]), size=(60, 1), key="patrones_excluir")],

        # --- Árbol / Símbolos -------------------------------------------------
        [
            sg.Checkbox("Mostrar funciones (árbol)", key="mostrar_funciones", default=config["mostrar_funciones"]),
            sg.Checkbox("Mostrar clases (árbol)", key="mostrar_clases", default=config["mostrar_clases"]),
            sg.Checkbox("Mostrar métodos (árbol)", key="mostrar_metodos", default=config["mostrar_metodos"]),
        ],
        [
            sg.Checkbox("Generar archivo de árbol", key="generar_arbol", default=config["generar_arbol"]),
            sg.Checkbox("Imprimir árbol por consola", key="imprimir_arbol", default=config["imprimir_arbol"]),
        ],
        [
            sg.Checkbox("Guardar log de errores", key="guardar_log_errores", default=config["guardar_log_errores"]),
        ],

        # --- Acciones ---------------------------------------------------------
        [
            sg.Button("Procesar", button_color=("white", "green")),
            sg.Button("Guardar Configuración"),
            sg.Button("Resetear Configuración"),
            sg.Button("Salir", button_color=("white", "red")),
        ],
    ]

    window = sg.Window("Herramienta de Transcripción y Árbol de Directorios", layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Salir"):
            break

        # ---------------------------------------------------------------------
        # Selección de carpetas
        # ---------------------------------------------------------------------
        if event == "btn_explorar_in":
            initial = _normalizar_dir(values.get("ruta_carpetas", ""), os.path.dirname(os.path.abspath(__file__)))
            folder = sg.popup_get_folder("Seleccione la carpeta a procesar", default_path=initial)
            if folder:
                window["ruta_carpetas"].update(folder)
                # UX: si la salida base estaba igual al antiguo input, la actualizamos también
                curr_out = (values.get("output_base_dir") or "").strip()
                if not curr_out or os.path.abspath(curr_out) == os.path.abspath(initial):
                    window["output_base_dir"].update(folder)

        if event == "btn_examinar_out":
            initial = _normalizar_dir(values.get("output_base_dir", ""), values.get("ruta_carpetas", ""))
            folder = sg.popup_get_folder("Seleccione la ruta base de salida", default_path=initial)
            if folder:
                window["output_base_dir"].update(folder)

        # ---------------------------------------------------------------------
        # Guardar / Reset
        # ---------------------------------------------------------------------
        if event == "Guardar Configuración":
            actualizar_config_desde_gui(config, values)
            # Normalizamos rutas antes de guardar
            config["ruta_carpetas"] = _normalizar_dir(config["ruta_carpetas"], os.path.dirname(os.path.abspath(__file__)))
            config["output_base_dir"] = _normalizar_dir(config["output_base_dir"], config["ruta_carpetas"])
            guardar_configuracion(config)
            sg.popup("Configuración guardada en config.json")

        if event == "Resetear Configuración":
            config = cargar_configuracion_por_defecto()
            _volcar_config_a_gui(window, config)
            guardar_configuracion(config)
            sg.popup("Se ha restaurado la configuración por defecto.")

        # ---------------------------------------------------------------------
        # Procesar
        # ---------------------------------------------------------------------
        if event == "Procesar":
            try:
                actualizar_config_desde_gui(config, values)

                # Normalizar rutas
                ruta_carpetas = _normalizar_dir(config["ruta_carpetas"], os.path.dirname(os.path.abspath(__file__)))
                output_base_dir = _normalizar_dir(config["output_base_dir"], ruta_carpetas)
                output_subdir_name = (config.get("output_subdir_name") or "").strip() or DEFAULT_OUTPUT_SUBDIR
                output_prefix = (config.get("output_prefix") or "").strip() or DEFAULT_OUTPUT_PREFIX

                # Validación de input
                if not os.path.exists(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no existe:\n{ruta_carpetas}")
                    continue
                if not os.path.isdir(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no es un directorio:\n{ruta_carpetas}")
                    continue

                # Ruta final de salida: base + subcarpeta
                salida_real = _ruta_salida_real(output_base_dir, output_subdir_name)

                # Determinar ficheros destino para confirmar sobrescritura
                modo_final = config["modo_procesamiento"]
                incluir_arbol = bool(config.get("generar_arbol"))
                nombres = _archivos_destino(output_prefix, modo_final, incluir_arbol)
                existentes = _existen_ficheros_destino(salida_real, nombres)

                # Crear carpeta de salida si no existe (NO es sobrescritura)
                try:
                    os.makedirs(salida_real, exist_ok=True)
                except OSError as e:
                    sg.popup_error(f"No se pudo crear la carpeta de salida:\n{salida_real}\n\n{e}")
                    continue

                # Confirmación SOLO si existen ficheros concretos a reescribir
                if existentes:
                    msg = "Se van a sobrescribir estos archivos:\n\n" + "\n".join(existentes) + "\n\n¿Desea continuar?"
                    resp = sg.popup_yes_no(msg)
                    if resp != "Yes":
                        continue

                # --- Transcripción ------------------------------------------------
                res_trans = transcribir_codigo(
                    ruta_base=ruta_carpetas,
                    modo=modo_final,
                    extensiones=config["extensiones"],
                    patrones_incluir=config["patrones_incluir"],
                    patrones_excluir=config["patrones_excluir"],
                    archivo_salida=output_prefix,
                    output_folder=salida_real,
                    guardar_log_errores=bool(config.get("guardar_log_errores")),
                )

                if not res_trans.get("ok"):
                    sg.popup_error(f"Fallo en transcripción:\n{res_trans.get('error', 'Error desconocido')}")
                    continue

                # --- Árbol --------------------------------------------------------
                ruta_arbol = ""
                if incluir_arbol:
                    ruta_arbol = os.path.join(salida_real, f"{output_prefix}_arbol.txt")

                generar_arbol_directorios(
                    ruta_base=ruta_carpetas,
                    modo=modo_final,
                    extensiones=config["extensiones"],
                    patrones_incluir=config["patrones_incluir"],
                    patrones_excluir=config["patrones_excluir"],
                    mostrar_funciones=config["mostrar_funciones"],
                    mostrar_clases=config["mostrar_clases"],
                    mostrar_metodos=config.get("mostrar_metodos", False),
                    imprimir=bool(config.get("imprimir_arbol", True)),
                    guardar_archivo=ruta_arbol,
                )

                # --- Resumen ------------------------------------------------------
                cont = res_trans.get("contadores", {})
                resumen = (
                    "Procesamiento finalizado.\n\n"
                    f"Salida: {salida_real}\n\n"
                    f"Procesados: {cont.get('procesados', 0)}\n"
                    f"Omitidos: {cont.get('omitidos', 0)}\n"
                    f"Errores: {cont.get('errores', 0)}\n"
                )

                sg.popup(resumen)

            except Exception as e:
                tb = traceback.format_exc(limit=5)
                sg.popup_error(f"Error inesperado:\n{e}\n\n{tb}")

    window.close()


# -----------------------------------------------------------------------------
# Entry point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    main()