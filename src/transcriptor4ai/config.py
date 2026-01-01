from __future__ import annotations

import json
import os

from transcriptor4ai.paths import DEFAULT_OUTPUT_SUBDIR


# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_PREFIX = "transcripcion"

# -----------------------------------------------------------------------------
# Configuración: defaults / load / save
# -----------------------------------------------------------------------------
def cargar_configuracion_por_defecto() -> dict:
    """
    Valores por defecto.

    - ruta_carpetas: carpeta a procesar (por defecto: directorio donde está main.py/app_core.py)
    - output_base_dir: ruta base de salida (por defecto: igual que ruta_carpetas)
    - output_subdir_name: subcarpeta que se crea dentro de output_base_dir
    - output_prefix: prefijo para los archivos generados
    """
    base = os.getcwd()
    return {
        "ruta_carpetas": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": DEFAULT_OUTPUT_PREFIX,
        "modo_procesamiento": "todo",  # Posibles: all, solo_modulos, solo_tests
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
    """
    Carga config.json si existe y hace merge sobre defaults.
    Si hay error de parseo, devuelve defaults.
    """
    defaults = cargar_configuracion_por_defecto()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                defaults.update(data)
        except Exception:
            pass
    return defaults


def guardar_configuracion(config: dict) -> None:
    """
    Guarda config.json.
    Lanza excepción si falla (para que el caller decida cómo informar).
    """
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
