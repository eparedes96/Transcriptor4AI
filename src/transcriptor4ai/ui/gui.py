from __future__ import annotations

import os
import traceback

import PySimpleGUI as sg

from transcriptor4ai import config as cfg
from transcriptor4ai import paths
from transcriptor4ai.transcription.service import transcribir_codigo
from transcriptor4ai.tree.service import generar_arbol_directorios

# -----------------------------------------------------------------------------
# Actualización config desde GUI (GUI-specific)
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


def volcar_config_a_gui(window: sg.Window, config: dict) -> None:
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

    # -------------------------
    # Cargar configuración
    # -------------------------
    config = cfg.cargar_configuracion()

    if not config.get("output_base_dir"):
        config["output_base_dir"] = config.get("ruta_carpetas") or os.path.dirname(os.path.abspath(__file__))

    # -------------------------
    # Layout
    # -------------------------
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

    # -------------------------
    # Event loop
    # -------------------------
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Salir"):
            break

        # ---------------------------------------------------------------------
        # Selección de carpetas
        # ---------------------------------------------------------------------
        if event == "btn_explorar_in":
            initial = paths.normalizar_dir(values.get("ruta_carpetas", ""), os.path.dirname(os.path.abspath(__file__)))
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

        # ---------------------------------------------------------------------
        # Guardar / Reset
        # ---------------------------------------------------------------------
        if event == "Guardar Configuración":
            try:
                actualizar_config_desde_gui(config, values)
                config["ruta_carpetas"] = paths.normalizar_dir(config["ruta_carpetas"], os.path.dirname(os.path.abspath(__file__)))
                config["output_base_dir"] = paths.normalizar_dir(config["output_base_dir"], config["ruta_carpetas"])
                cfg.guardar_configuracion(config)
                sg.popup("Configuración guardada en config.json")
            except Exception as e:
                sg.popup_error(f"No se pudo guardar configuración:\n{e}")

        if event == "Resetear Configuración":
            config = cfg.cargar_configuracion_por_defecto()
            volcar_config_a_gui(window, config)
            try:
                cfg.guardar_configuracion(config)
            except Exception as e:
                sg.popup_error(f"No se pudo guardar configuración por defecto:\n{e}")
            sg.popup("Se ha restaurado la configuración por defecto.")

        # ---------------------------------------------------------------------
        # Procesar
        # ---------------------------------------------------------------------
        if event == "Procesar":
            try:
                actualizar_config_desde_gui(config, values)

                # Normalizar rutas
                ruta_carpetas = paths.normalizar_dir(config["ruta_carpetas"], os.path.dirname(os.path.abspath(__file__)))
                output_base_dir = paths.normalizar_dir(config["output_base_dir"], ruta_carpetas)
                output_subdir_name = (config.get("output_subdir_name") or "").strip() or paths.DEFAULT_OUTPUT_SUBDIR
                output_prefix = (config.get("output_prefix") or "").strip() or cfg.DEFAULT_OUTPUT_PREFIX

                # Validación de input
                if not os.path.exists(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no existe:\n{ruta_carpetas}")
                    continue
                if not os.path.isdir(ruta_carpetas):
                    sg.popup_error(f"La ruta a procesar no es un directorio:\n{ruta_carpetas}")
                    continue

                # Ruta final de salida
                salida_real = paths.ruta_salida_real(output_base_dir, output_subdir_name)

                # Determinar ficheros destino para confirmar sobrescritura
                modo_final = config["modo_procesamiento"]
                incluir_arbol = bool(config.get("generar_arbol"))
                nombres = paths.archivos_destino(output_prefix, modo_final, incluir_arbol)
                existentes = paths.existen_ficheros_destino(salida_real, nombres)

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