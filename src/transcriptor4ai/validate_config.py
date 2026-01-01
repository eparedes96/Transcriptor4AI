# src/transcriptor4ai/validate_config.py
from __future__ import annotations

from typing import Any, Dict, List, Tuple
import logging

from transcriptor4ai.config import cargar_configuracion_por_defecto
from transcriptor4ai.filtering import (
    default_extensiones,
    default_patrones_incluir,
    default_patrones_excluir,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------
def validate_config(
    config: Any,
    *,
    strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Valida y normaliza el dict de configuración para que el pipeline (y UI/CLI)
    puedan operar sin defensiva repetitiva.

    - Nunca toca el filesystem.
    - Garantiza llaves mínimas, tipos esperados y valores por defecto coherentes.
    - Devuelve: (config_normalizada, warnings)

    strict=False:
      - intenta corregir y añade warnings.
      - ante config inválida (no dict), cae a defaults.

    strict=True:
      - ante errores de tipo/valor, lanza ValueError/TypeError.

    Nota: esto NO decide rutas finales (eso es del pipeline). Solo sanea el esquema.
    """
    warnings: List[str] = []
    defaults = cargar_configuracion_por_defecto()

    # -------------------------------------------------------------------------
    # 1) Validación base: dict
    # -------------------------------------------------------------------------
    if not isinstance(config, dict):
        msg = f"Config inválida: se esperaba dict, se recibió {type(config).__name__}."
        if strict:
            raise TypeError(msg)
        warnings.append(msg + " Se usan defaults.")
        logger.warning(msg)
        return defaults, warnings

    merged: Dict[str, Any] = dict(defaults)
    merged.update(config)

    # -------------------------------------------------------------------------
    # 2) Normalización de strings obligatorias
    # -------------------------------------------------------------------------
    merged["ruta_carpetas"] = _as_str(merged.get("ruta_carpetas"), defaults["ruta_carpetas"], "ruta_carpetas", warnings, strict)
    merged["output_base_dir"] = _as_str(merged.get("output_base_dir"), defaults["output_base_dir"], "output_base_dir", warnings, strict)
    merged["output_subdir_name"] = _as_str(merged.get("output_subdir_name"), defaults["output_subdir_name"], "output_subdir_name", warnings, strict)
    merged["output_prefix"] = _as_str(merged.get("output_prefix"), defaults["output_prefix"], "output_prefix", warnings, strict)

    # -------------------------------------------------------------------------
    # 3) Normalización de enums / flags
    # -------------------------------------------------------------------------
    merged["modo_procesamiento"] = _as_modo(
        merged.get("modo_procesamiento"),
        defaults["modo_procesamiento"],
        warnings,
        strict,
    )

    merged["mostrar_funciones"] = _as_bool(merged.get("mostrar_funciones"), defaults["mostrar_funciones"], "mostrar_funciones", warnings, strict)
    merged["mostrar_clases"] = _as_bool(merged.get("mostrar_clases"), defaults["mostrar_clases"], "mostrar_clases", warnings, strict)
    merged["mostrar_metodos"] = _as_bool(merged.get("mostrar_metodos"), defaults["mostrar_metodos"], "mostrar_metodos", warnings, strict)

    merged["generar_arbol"] = _as_bool(merged.get("generar_arbol"), defaults["generar_arbol"], "generar_arbol", warnings, strict)
    merged["imprimir_arbol"] = _as_bool(merged.get("imprimir_arbol"), defaults["imprimir_arbol"], "imprimir_arbol", warnings, strict)
    merged["guardar_log_errores"] = _as_bool(merged.get("guardar_log_errores"), defaults["guardar_log_errores"], "guardar_log_errores", warnings, strict)

    # -------------------------------------------------------------------------
    # 4) Normalización de listas: extensiones y patrones
    # -------------------------------------------------------------------------
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
# Helpers internos
# -----------------------------------------------------------------------------
def _as_str(value: Any, fallback: str, field: str, warnings: List[str], strict: bool) -> str:
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip()
        return v if v else fallback
    msg = f"Campo '{field}' inválido: se esperaba str, se recibió {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(msg + " Se usa fallback.")
    logger.warning(msg)
    return fallback


def _as_bool(value: Any, fallback: bool, field: str, warnings: List[str], strict: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback

    if not strict:
        if isinstance(value, (int, float)) and value in (0, 1):
            warnings.append(f"Campo '{field}' convertido desde número {value} a bool.")
            return bool(value)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in ("true", "1", "yes", "y", "si", "sí"):
                warnings.append(f"Campo '{field}' convertido desde str '{value}' a bool True.")
                return True
            if s in ("false", "0", "no", "n"):
                warnings.append(f"Campo '{field}' convertido desde str '{value}' a bool False.")
                return False

    msg = f"Campo '{field}' inválido: se esperaba bool, se recibió {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(msg + " Se usa fallback.")
    logger.warning(msg)
    return fallback


def _as_list_str(value: Any, fallback: List[str], field: str, warnings: List[str], strict: bool) -> List[str]:
    if value is None:
        return list(fallback)

    if isinstance(value, str) and not strict:
        items = [x.strip() for x in value.split(",") if x.strip()]
        if items:
            warnings.append(f"Campo '{field}' convertido desde str CSV a lista.")
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
                msg = f"Campo '{field}[{i}]' inválido: se esperaba str, se recibió {type(item).__name__}."
                if strict:
                    raise TypeError(msg)
                warnings.append(msg + " Elemento descartado.")
                logger.warning(msg)
        return out if out else list(fallback)

    msg = f"Campo '{field}' inválido: se esperaba list[str], se recibió {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(msg + " Se usa fallback.")
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
        msg = f"modo_procesamiento inválido: '{value}'. Permitidos: {sorted(allowed)}."
        if strict:
            raise ValueError(msg)
        warnings.append(msg + f" Se usa fallback '{fallback}'.")
        logger.warning(msg)
        return fallback

    msg = f"modo_procesamiento inválido: se esperaba str, se recibió {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(msg + f" Se usa fallback '{fallback}'.")
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
                raise ValueError(f"Extensión inválida '{ext}': debe empezar por '.'.")
            warnings.append(f"Extensión '{ext}' corregida a '.{e}'.")
            e = "." + e
        out.append(e)
    return out if out else default_extensiones()