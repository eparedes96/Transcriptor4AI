# main.py
import os
import json
import PySimpleGUI as sg

from code_transcriptor import transcribir_codigo
from tree_generator import generar_arbol_directorios

# Archivo donde se guarda la configuración
CONFIG_FILE = "config.json"


def cargar_configuracion_por_defecto():
    """
    Retorna los valores por defecto de la configuración.
    La ruta de carpeta es la del proyecto actual (la carpeta donde se encuentra este script).
    """
    return {
        "ruta_carpetas": os.path.dirname(os.path.abspath(__file__)),  # Ruta del proyecto actual
        "modo_procesamiento": "todo",  # Valores posibles: todo, solo_modulos, solo_tests
        "archivo_salida": "transcripcion",
        "extensiones": [".py"],
        "patrones_incluir": [".*"],
        "patrones_excluir": ["^__init__\\.py$", ".*\\.pyc$", "^\\."],
        "mostrar_funciones": False,
        "mostrar_clases": False,
        "guardar_archivo_arbol": ""
    }


def cargar_configuracion():
    """
    Carga la configuración desde un archivo JSON si existe,
    de lo contrario retorna la configuración por defecto.
    """
    defaults = cargar_configuracion_por_defecto()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Mezclamos data con defaults para rellenar ausentes
            defaults.update(data)
        except:
            pass
    return defaults


def guardar_configuracion(config):
    """
    Guarda la configuración en un archivo JSON.
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)


def main():
    sg.theme("SystemDefault")  # Escoge el tema que quieras

    # Cargamos la configuración previa o la por defecto
    config = cargar_configuracion()

    # Definimos el layout de la ventana
    layout = [
        [sg.Text("Ruta de la carpeta a procesar:"),
         sg.Input(size=(40, 1), key="ruta_carpetas"),
         sg.FolderBrowse("Explorar")],

        [sg.Text("Modo de procesamiento:")],
        [sg.Radio("Todo (módulos + tests)", "RADIO1", key="modo_todo",
                  default=(config["modo_procesamiento"] == "todo")),
         sg.Radio("Solo Módulos", "RADIO1", key="modo_modulos",
                  default=(config["modo_procesamiento"] == "solo_modulos")),
         sg.Radio("Solo Tests", "RADIO1", key="modo_tests", default=(config["modo_procesamiento"] == "solo_tests"))],

        [sg.Text("Archivo de salida (prefijo para .txt):"), sg.Input(size=(40, 1), key="archivo_salida")],

        [sg.Text("Extensiones (separadas por coma):"), sg.Input(size=(40, 1), key="extensiones")],

        [sg.Text("Patrones Incluir (lista separada por comas):"), sg.Input(size=(40, 1), key="patrones_incluir")],
        [sg.Text("Patrones Excluir (lista separada por comas):"), sg.Input(size=(40, 1), key="patrones_excluir")],

        [sg.Checkbox("Mostrar funciones", key="mostrar_funciones")],
        [sg.Checkbox("Mostrar clases", key="mostrar_clases")],

        [sg.Text("Guardar archivo árbol (opcional):"), sg.Input(size=(40, 1), key="guardar_archivo_arbol"),
         sg.FileSaveAs("Examinar")],

        [sg.Button("Procesar", button_color=("white", "green")),
         sg.Button("Guardar Configuración"),
         sg.Button("Resetear Configuración"),
         sg.Button("Salir", button_color=("white", "red"))]
    ]

    window = sg.Window("Herramienta de Transcripción y Árbol de Directorios", layout, finalize=True)

    # Inicializamos campos con la config actual
    window["ruta_carpetas"].update(config["ruta_carpetas"])
    window["archivo_salida"].update(config["archivo_salida"])
    window["extensiones"].update(",".join(config["extensiones"]))
    window["patrones_incluir"].update(",".join(config["patrones_incluir"]))
    window["patrones_excluir"].update(",".join(config["patrones_excluir"]))
    window["mostrar_funciones"].update(config["mostrar_funciones"])
    window["mostrar_clases"].update(config["mostrar_clases"])
    window["guardar_archivo_arbol"].update(config["guardar_archivo_arbol"])

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, "Salir"):
            break

        if event == "Guardar Configuración":
            # Actualizamos el dict config con los valores de la ventana
            actualizar_config_desde_gui(config, values, window)
            guardar_configuracion(config)
            sg.popup("Configuración guardada en config.json")

        if event == "Resetear Configuración":
            # Cargamos la configuración por defecto
            def_conf = cargar_configuracion_por_defecto()
            # Actualizamos la ventana
            window["ruta_carpetas"].update(def_conf["ruta_carpetas"])
            window["modo_todo"].update(def_conf["modo_procesamiento"] == "todo")
            window["modo_modulos"].update(def_conf["modo_procesamiento"] == "solo_modulos")
            window["modo_tests"].update(def_conf["modo_procesamiento"] == "solo_tests")
            window["archivo_salida"].update(def_conf["archivo_salida"])
            window["extensiones"].update(",".join(def_conf["extensiones"]))
            window["patrones_incluir"].update(",".join(def_conf["patrones_incluir"]))
            window["patrones_excluir"].update(",".join(def_conf["patrones_excluir"]))
            window["mostrar_funciones"].update(def_conf["mostrar_funciones"])
            window["mostrar_clases"].update(def_conf["mostrar_clases"])
            window["guardar_archivo_arbol"].update(def_conf["guardar_archivo_arbol"])
            # Actualizamos la configuración en memoria y la guardamos en el JSON
            config = def_conf
            guardar_configuracion(config)
            sg.popup("Se ha restaurado la configuración por defecto.")

        if event == "Procesar":
            # 1) Actualizar config con datos de la ventana
            actualizar_config_desde_gui(config, values, window)

            # 2) Llamar al code_transcriptor para generar los .txt
            modo_final = config["modo_procesamiento"]
            transcribir_codigo(
                ruta_base=config["ruta_carpetas"],
                modo=modo_final,
                extensiones=config["extensiones"],
                patrones_incluir=config["patrones_incluir"],
                patrones_excluir=config["patrones_excluir"],
                archivo_salida=config["archivo_salida"]
            )

            # 3) Generar el árbol de directorios en consola (y opcionalmente a archivo)
            generar_arbol_directorios(
                ruta_base=config["ruta_carpetas"],
                modo=modo_final,
                extensiones=config["extensiones"],
                patrones_incluir=config["patrones_incluir"],
                patrones_excluir=config["patrones_excluir"],
                mostrar_funciones=config["mostrar_funciones"],
                mostrar_clases=config["mostrar_clases"],
                guardar_archivo=config["guardar_archivo_arbol"]
            )

            sg.popup(
                "¡Procesamiento finalizado!\nRevisa la consola para ver el árbol.\nSe han generado (según el modo) los archivos de transcripción de código.")

    window.close()


def actualizar_config_desde_gui(config, values, window):
    """
    Toma los valores del formulario y los vuelca en el dict config.
    """
    config["ruta_carpetas"] = values["ruta_carpetas"]

    if values["modo_todo"]:
        config["modo_procesamiento"] = "todo"
    elif values["modo_modulos"]:
        config["modo_procesamiento"] = "solo_modulos"
    elif values["modo_tests"]:
        config["modo_procesamiento"] = "solo_tests"

    config["archivo_salida"] = values["archivo_salida"]
    # Convertimos las listas separadas por comas a lista real
    config["extensiones"] = [ext.strip() for ext in values["extensiones"].split(",") if ext.strip()]
    config["patrones_incluir"] = [pat.strip() for pat in values["patrones_incluir"].split(",") if pat.strip()]
    config["patrones_excluir"] = [pat.strip() for pat in values["patrones_excluir"].split(",") if pat.strip()]

    config["mostrar_funciones"] = values["mostrar_funciones"]
    config["mostrar_clases"] = values["mostrar_clases"]
    config["guardar_archivo_arbol"] = values["guardar_archivo_arbol"]


if __name__ == "__main__":
    main()
