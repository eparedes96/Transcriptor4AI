# app_core.py
# -----------------------------------------------------------------------------
# Core (sin GUI) para:
# - Cargar/guardar configuración (config.json)
# - Helpers puros de rutas y ficheros destino
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import json
from typing import List


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

    - ruta_carpetas: carpeta a procesar (por defecto: directorio donde está main.py/app_core.py)
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


# -----------------------------------------------------------------------------
# Helpers de rutas / sobrescritura
# -----------------------------------------------------------------------------

def normalizar_dir(path: str, fallback: str) -> str:
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


def ruta_salida_real(output_base_dir: str, output_subdir_name: str) -> str:
    """
    Ruta donde se generan los ficheros:
      output_base_dir / output_subdir_name
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)


def archivos_destino(prefix: str, modo: str, incluir_arbol: bool) -> List[str]:
    """
    Devuelve los nombres de ficheros (no rutas) que se generarían.
    """
    files: List[str] = []
    if modo in ("todo", "solo_tests"):
        files.append(f"{prefix}_tests.txt")
    if modo in ("todo", "solo_modulos"):
        files.append(f"{prefix}_modulos.txt")
    if incluir_arbol:
        files.append(f"{prefix}_arbol.txt")
    return files


def existen_ficheros_destino(output_dir: str, names: List[str]) -> List[str]:
    """
    Devuelve la lista de ficheros (rutas completas) que YA existen.
    """
    existentes: List[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existentes.append(full)
    return existentes