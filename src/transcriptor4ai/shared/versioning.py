from __future__ import annotations

"""
Semantic Versioning Utilities.

Provides robust comparison logic for application versions following the 
SemVer pattern. This module centralizes version parsing to ensure 
consistency across update checks and configuration migrations.
"""

import logging
from typing import Tuple

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API
# ==============================================================================

def is_newer(current: str, latest: str) -> bool:
    """
    Determine if the latest version string is semantically higher than current.

    Supports versions with or without 'v' prefix (e.g., 'v2.1.0' vs '2.0.5').

    Args:
        current: The currently running version string.
        latest: The version string discovered from a remote source.

    Returns:
        bool: True if latest > current, False otherwise or if parsing fails.
    """
    # 1. VALIDACIÓN: Evitar comparaciones innecesarias si son idénticas
    if current.strip() == latest.strip():
        return False

    try:
        # 2. PROCESAMIENTO: Normalizar ambos strings a tuplas de enteros
        current_tuple = _parse_version(current)
        latest_tuple = _parse_version(latest)

        # 3. RETORNO: Comparación nativa de tuplas de Python (léxica por posición)
        return latest_tuple > current_tuple

    except (ValueError, TypeError, IndexError) as e:
        logger.warning(f"Versioning: Failed to compare '{current}' and '{latest}': {e}")
        return False


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Convert a version string into a comparable tuple of integers.

    Example: "v2.1.0-alpha" -> (2, 1, 0)

    Args:
        version_str: Raw version string.

    Returns:
        Tuple[int, ...]: Integer sequence representing Major, Minor, Patch.
    """
    # Limpiar prefijo 'v' y espacios
    clean_str = version_str.lower().lstrip("v").strip()

    # Dividir por puntos y extraer solo la parte numérica de cada segmento
    # Esto ignora sufijos como '-beta' o '+build' para la comparación básica
    parts = clean_str.split(".")

    numeric_parts = []
    for p in parts:
        # Extraer solo dígitos iniciales del segmento
        numeric_val = "".join(filter(str.isdigit, p))
        if numeric_val:
            numeric_parts.append(int(numeric_val))
        else:
            # Si un segmento no tiene números (ej: "v.x"), se asume 0
            numeric_parts.append(0)

    # Asegurar al menos 3 componentes (Major, Minor, Patch)
    while len(numeric_parts) < 3:
        numeric_parts.append(0)

    return tuple(numeric_parts)