from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from transcriptor4ai.config import cargar_configuracion_por_defecto
from transcriptor4ai.filtering import (
    default_extensiones,
    default_patrones_incluir,
    default_patrones_excluir,
)

logger = logging.getLogger(__name__)


def validate_config(
    config: Any,
    *,
    strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and normalize the configuration dictionary.

    This function acts as a gatekeeper to ensure the pipeline receives
    sanitized data. It does not touch the filesystem.

    Args:
        config: The raw configuration dictionary (or potentially invalid type).
        strict: If True, raises TypeError/ValueError on invalid data.
                If False, falls back to defaults and logs warnings.

    Returns:
        A tuple containing:
        1. The normalized configuration dictionary.
        2. A list of warning messages (strings).
    """
    warnings: List[str] = []
    defaults = cargar_configuracion_por_defecto()

    # 1. Base Validation: Type Check
    if not isinstance(config, dict):
        msg = f"Invalid config type: expected dict, received {type(config).__name__}."
        if strict:
            raise TypeError(msg)
        warnings.append(f"{msg} Using defaults.")
        logger.warning(msg)
        return defaults, warnings

    # Start with defaults and update with provided config
    merged: Dict[str, Any] = dict(defaults)
    merged.update(config)

    # 2. String Normalization
    merged["ruta_carpetas"] = _as_str(
        merged.get("ruta_carpetas"),
        defaults["ruta_carpetas"],
        "ruta_carpetas",
        warnings,
        strict
    )
    merged["output_base_dir"] = _as_str(
        merged.get("output_base_dir"),
        defaults["output_base_dir"],
        "output_base_dir",
        warnings,
        strict
    )
    merged["output_subdir_name"] = _as_str(
        merged.get("output_subdir_name"),
        defaults["output_subdir_name"],
        "output_subdir_name",
        warnings,
        strict
    )
    merged["output_prefix"] = _as_str(
        merged.get("output_prefix"),
        defaults["output_prefix"],
        "output_prefix",
        warnings,
        strict
    )

    # 3. Enums and Flags Normalization
    merged["modo_procesamiento"] = _as_modo(
        merged.get("modo_procesamiento"),
        defaults["modo_procesamiento"],
        warnings,
        strict,
    )

    merged["mostrar_funciones"] = _as_bool(
        merged.get("mostrar_funciones"),
        defaults["mostrar_funciones"],
        "mostrar_funciones",
        warnings,
        strict
    )
    merged["mostrar_clases"] = _as_bool(
        merged.get("mostrar_clases"),
        defaults["mostrar_clases"],
        "mostrar_clases",
        warnings,
        strict
    )
    merged["mostrar_metodos"] = _as_bool(
        merged.get("mostrar_metodos"),
        defaults["mostrar_metodos"],
        "mostrar_metodos",
        warnings,
        strict
    )

    merged["generar_arbol"] = _as_bool(
        merged.get("generar_arbol"),
        defaults["generar_arbol"],
        "generar_arbol",
        warnings,
        strict
    )
    merged["imprimir_arbol"] = _as_bool(
        merged.get("imprimir_arbol"),
        defaults["imprimir_arbol"],
        "imprimir_arbol",
        warnings,
        strict
    )
    merged["guardar_log_errores"] = _as_bool(
        merged.get("guardar_log_errores"),
        defaults["guardar_log_errores"],
        "guardar_log_errores",
        warnings,
        strict
    )

    # 4. Lists Normalization: Extensions and Patterns
    merged["extensiones"] = _as_list_str(
        merged.get("extensiones"),
        default_extensiones(),
        "extensiones",
        warnings,
        strict,
    )
    merged["extensiones"] = _normalize_extensions(merged["extensiones"], warnings, strict)

    merged["patrones_incluir"] = _as_list_str(
        merged.get("patrones_incluir"),
        default_patrones_incluir(),
        "patrones_incluir",
        warnings,
        strict,
    )
    merged["patrones_excluir"] = _as_list_str(
        merged.get("patrones_excluir"),
        default_patrones_excluir(),
        "patrones_excluir",
        warnings,
        strict,
    )

    return merged, warnings


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------

def _as_str(value: Any, fallback: str, field: str, warnings: List[str], strict: bool) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip()
        return v if v else fallback
    msg = f"Invalid field '{field}': expected str, received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    logger.warning(msg)
    return fallback


def _as_bool(value: Any, fallback: bool, field: str, warnings: List[str], strict: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback

    if not strict:
        if isinstance(value, (int, float)) and value in (0, 1):
            warnings.append(f"Field '{field}' converted from number {value} to bool.")
            return bool(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in ("true", "1", "yes", "y", "si", "sí"):
                warnings.append(f"Field '{field}' converted from str '{value}' to True.")
                return True
            if s in ("false", "0", "no", "n"):
                warnings.append(f"Field '{field}' converted from str '{value}' to False.")
                return False

    msg = f"Invalid field '{field}': expected bool, received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    logger.warning(msg)
    return fallback


def _as_list_str(value: Any, fallback: List[str], field: str, warnings: List[str], strict: bool) -> List[str]:
    if value is None:
        return list(fallback)

    if isinstance(value, str) and not strict:
        items = [x.strip() for x in value.split(",") if x.strip()]
        if items:
            warnings.append(f"Field '{field}' converted from CSV string to list.")
            return items
        return list(fallback)

    if isinstance(value, list):
        out: List[str] = []
        for i, item in enumerate(value):
            if isinstance(item, str):
                s = item.strip()
                if s:
                    out.append(s)
            else:
                msg = f"Invalid item in '{field}[{i}]': expected str, received {type(item).__name__}."
                if strict:
                    raise TypeError(msg)
                warnings.append(f"{msg} Item discarded.")
                logger.warning(msg)
        return out if out else list(fallback)

    msg = f"Invalid field '{field}': expected list[str], received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    logger.warning(msg)
    return list(fallback)


def _as_modo(value: Any, fallback: str, warnings: List[str], strict: bool) -> str:
    allowed = {"todo", "solo_modulos", "solo_tests"}
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip().lower()
        if v in allowed:
            return v
        msg = f"Invalid 'modo_procesamiento': '{value}'. Allowed: {sorted(allowed)}."
        if strict:
            raise ValueError(msg)
        warnings.append(f"{msg} Using fallback '{fallback}'.")
        logger.warning(msg)
        return fallback

    msg = f"Invalid 'modo_procesamiento': expected str, received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback '{fallback}'.")
    logger.warning(msg)
    return fallback


def _normalize_extensions(exts: List[str], warnings: List[str], strict: bool) -> List[str]:
    out: List[str] = []
    for ext in exts:
        e = ext.strip()
        if not e:
            continue
        if not e.startswith("."):
            if strict:
                raise ValueError(f"Invalid extension '{ext}': must start with '.'.")
            warnings.append(f"Extension '{ext}' corrected to '.{e}'.")
            e = "." + e
        out.append(e)
    return out if out else default_extensiones()