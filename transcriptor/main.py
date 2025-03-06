# main.py
import os
import json
import PySimpleGUI as sg

from transcriptor.code_transcriptor import transcribir_codigo
from transcriptor.tree_generator import generar_arbol_directorios

CONFIG_FILE = "config.json"

def cargar_configuracion_por_defecto():
    """
    Retorna los valores por defecto de la configuración.
    La ruta de entrada es la del proyecto actual.
    La carpeta de salida por defecto se llama "transcripcion".
    """
    return {
        "ruta_carpetas": os.path.dirname(os.path.abspath(__file__)),
        "modo_procesamiento": "todo",  # Posibles: todo, solo_modulos, solo_tests
        "carpeta_salida": "transcripcion",
        "extensiones": [".py"],
        "patrones_incluir": [".*"],
        "patrones_excluir": ["^__init__\\.py$", ".*\\.pyc$", "^(\\.git|\\.idea|_pycache_)", "^\\."],
        "mostrar_funciones": False,
        "mostrar_clases": False,
        "generar_arbol": False  # Si True se genera el archivo de árbol.
    }

def cargar_configuracion():
    defaults = cargar_configuracion_por_defecto()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            defaults.update(data)
        except:
            pass
    return defaults

def guardar_configuracion(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

def main():
    sg.theme("SystemDefault")
    config = cargar_configuracion()
    layout = [
        [sg.Text("Ruta de la carpeta a procesar:"),
         sg.Input(default_text=config["ruta_carpetas"], size=(40,1), key="ruta_carpetas"),
         sg.Button("Explorar", key="btn_explorar")],
        [sg.Text("Carpeta de salida:"),
         sg.Input(default_text=config["carpeta_salida"], size=(40,1), key="carpeta_salida"),
         sg.Button("Examinar", key="btn_examinar")],
        [sg.Text("Modo de procesamiento:")],
        [sg.Radio("Todo (módulos + tests)", "RADIO1", key="modo_todo", default=(config["modo_procesamiento"]=="todo")),
         sg.Radio("Solo Módulos", "RADIO1", key="modo_modulos", default=(config["modo_procesamiento"]=="solo_modulos")),
         sg.Radio("Solo Tests", "RADIO1", key="modo_tests", default=(config["modo_procesamiento"]=="solo_tests"))],
        [sg.Text("Extensiones (separadas por coma):"), sg.Input(",".join(config["extensiones"]), size=(40,1), key="extensiones")],
        [sg.Text("Patrones Incluir (lista separada por comas):"), sg.Input(",".join(config["patrones_incluir"]), size=(40,1), key="patrones_incluir")],
        [sg.Text("Patrones Excluir (lista separada por comas):"), sg.Input(",".join(config["patrones_excluir"]), size=(40,1), key="patrones_excluir")],
        [sg.Checkbox("Mostrar funciones", key="mostrar_funciones", default=config["mostrar_funciones"]),
         sg.Checkbox("Mostrar clases", key="mostrar_clases", default=config["mostrar_clases"])],
        [sg.Checkbox("Generar archivo de árbol", key="generar_arbol", default=config["generar_arbol"])],
        [sg.Button("Procesar", button_color=("white","green")),
         sg.Button("Guardar Configuración"),
         sg.Button("Resetear Configuración"),
         sg.Button("Salir", button_color=("white","red"))]
    ]
    window = sg.Window("Herramienta de Transcripción y Árbol de Directorios", layout, finalize=True)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Salir"):
            break

        # Botón Explorar: usar la ruta actual de "ruta_carpetas" como directorio inicial
        if event == "btn_explorar":
            initial = window["ruta_carpetas"].get()
            folder = sg.popup_get_folder("Seleccione la carpeta a procesar", default_path=initial)
            if folder:
                window["ruta_carpetas"].update(folder)

        # Botón Examinar: usar la ruta actual de "ruta_carpetas" como directorio inicial para la carpeta de salida
        if event == "btn_examinar":
            initial = window["ruta_carpetas"].get()
            folder = sg.popup_get_folder("Seleccione la carpeta de salida", default_path=initial)
            if folder:
                window["carpeta_salida"].update(folder)

        if event == "Guardar Configuración":
            actualizar_config_desde_gui(config, values)
            guardar_configuracion(config)
            sg.popup("Configuración guardada en config.json")

        if event == "Resetear Configuración":
            def_conf = cargar_configuracion_por_defecto()
            window["ruta_carpetas"].update(def_conf["ruta_carpetas"])
            window["carpeta_salida"].update(def_conf["carpeta_salida"])
            window["modo_todo"].update(def_conf["modo_procesamiento"]=="todo")
            window["modo_modulos"].update(def_conf["modo_procesamiento"]=="solo_modulos")
            window["modo_tests"].update(def_conf["modo_procesamiento"]=="solo_tests")
            window["extensiones"].update(",".join(def_conf["extensiones"]))
            window["patrones_incluir"].update(",".join(def_conf["patrones_incluir"]))
            window["patrones_excluir"].update(",".join(def_conf["patrones_excluir"]))
            window["mostrar_funciones"].update(def_conf["mostrar_funciones"])
            window["mostrar_clases"].update(def_conf["mostrar_clases"])
            window["generar_arbol"].update(def_conf["generar_arbol"])
            config = def_conf
            guardar_configuracion(config)
            sg.popup("Se ha restaurado la configuración por defecto.")

        if event == "Procesar":
            actualizar_config_desde_gui(config, values)
            salida_input = values["carpeta_salida"]
            if not os.path.isabs(salida_input):
                salida_input = os.path.join(os.path.dirname(__file__), salida_input)
            if os.path.exists(salida_input):
                resp = sg.popup_yes_no(f"La carpeta de salida\n{salida_input}\nya existe. ¿Desea continuar y sobrescribir archivos?")
                if resp != "Yes":
                    continue
            else:
                os.makedirs(salida_input)
            modo_final = config["modo_procesamiento"]
            transcribir_codigo(
                ruta_base=config["ruta_carpetas"],
                modo=modo_final,
                extensiones=config["extensiones"],
                patrones_incluir=config["patrones_incluir"],
                patrones_excluir=config["patrones_excluir"],
                archivo_salida=config["carpeta_salida"],
                output_folder=salida_input
            )
            ruta_arbol = ""
            if config["generar_arbol"]:
                ruta_arbol = os.path.join(salida_input, f"{config['carpeta_salida']}_arbol.txt")
            generar_arbol_directorios(
                ruta_base=config["ruta_carpetas"],
                modo=modo_final,
                extensiones=config["extensiones"],
                patrones_incluir=config["patrones_incluir"],
                patrones_excluir=config["patrones_excluir"],
                mostrar_funciones=config["mostrar_funciones"],
                mostrar_clases=config["mostrar_clases"],
                guardar_archivo=ruta_arbol
            )
            sg.popup("¡Procesamiento finalizado!\nRevisa la consola para ver el árbol.\nSe han generado los archivos en la carpeta de salida.")

    window.close()

def actualizar_config_desde_gui(config, values):
    config["ruta_carpetas"] = values["ruta_carpetas"]
    config["carpeta_salida"] = values["carpeta_salida"]
    if values["modo_todo"]:
        config["modo_procesamiento"] = "todo"
    elif values["modo_modulos"]:
        config["modo_procesamiento"] = "solo_modulos"
    elif values["modo_tests"]:
        config["modo_procesamiento"] = "solo_tests"
    config["extensiones"] = [ext.strip() for ext in values["extensiones"].split(",") if ext.strip()]
    config["patrones_incluir"] = [pat.strip() for pat in values["patrones_incluir"].split(",") if pat.strip()]
    config["patrones_excluir"] = [pat.strip() for pat in values["patrones_excluir"].split(",") if pat.strip()]
    config["mostrar_funciones"] = values["mostrar_funciones"]
    config["mostrar_clases"] = values["mostrar_clases"]
    config["generar_arbol"] = values["generar_arbol"]

if __name__ == "__main__":
    main()
