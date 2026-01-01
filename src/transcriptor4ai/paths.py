from __future__ import annotations

import os
from typing import List, Tuple, Optional

# -----------------------------------------------------------------------------
# Constantes
# -----------------------------------------------------------------------------
DEFAULT_OUTPUT_SUBDIR = "transcript"

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


def _safe_mkdir(path: str) -> Tuple[bool, Optional[str]]:
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except OSError as e:
        return False, str(e)