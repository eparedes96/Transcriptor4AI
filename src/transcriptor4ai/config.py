from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict

from transcriptor4ai.paths import DEFAULT_OUTPUT_SUBDIR

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CONFIG_FILE = "config.json"
DEFAULT_OUTPUT_PREFIX = "transcripcion"


# -----------------------------------------------------------------------------
# Configuration: Load / Save / Defaults
# -----------------------------------------------------------------------------
def cargar_configuracion_por_defecto() -> Dict[str, Any]:
    """
    Return the default configuration dictionary.

    Defaults:
    - ruta_carpetas: Current working directory.
    - output_base_dir: Current working directory.
    - output_subdir_name: 'transcript'.
    - processing mode: 'todo' (all).
    - exclusions: Common noise files (__init__.py, .git, __pycache__).
    """
    base = os.getcwd()
    return {
        "ruta_carpetas": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": DEFAULT_OUTPUT_PREFIX,
        "modo_procesamiento": "todo",  # Options: todo, solo_modulos, solo_tests
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


def cargar_configuracion() -> Dict[str, Any]:
    """
    Load 'config.json' if it exists and merge with defaults.
    Returns defaults if the file is missing or invalid.
    """
    defaults = cargar_configuracion_por_defecto()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                defaults.update(data)
                logger.debug(f"Configuration loaded from {CONFIG_FILE}")
            else:
                logger.warning(f"Invalid config file format in {CONFIG_FILE}. Using defaults.")
        except Exception as e:
            logger.warning(f"Failed to load {CONFIG_FILE}: {e}. Using defaults.")
    return defaults


def guardar_configuracion(config: Dict[str, Any]) -> None:
    """
    Save the configuration to 'config.json'.
    Raises OSError if writing fails.
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
    except OSError as e:
        logger.error(f"Failed to save configuration: {e}")
        raise