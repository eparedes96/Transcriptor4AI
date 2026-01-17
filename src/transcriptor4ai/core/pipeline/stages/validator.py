from __future__ import annotations

"""
Configuration Validation Service.

Acts as the primary gatekeeper for the pipeline, ensuring that the configuration 
dictionary conforms to the expected schema. Handles type coercion, path 
normalization, and default value injection to maintain execution stability.
"""

import logging
from typing import Any, Dict, List, Tuple

from transcriptor4ai.core.pipeline.components.filters import (
    default_extensions,
    default_include_patterns,
    default_exclude_patterns,
)
from transcriptor4ai.domain.config import get_default_config

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def validate_config(
        config: Any,
        *,
        strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and normalize the provided configuration dictionary.

    Ensures data integrity by converting untrusted inputs (e.g., from CLI or GUI)
    into strictly typed parameters. Fills missing keys with domain defaults.

    Args:
        config: Raw configuration data (usually a dictionary).
        strict: If True, raises exceptions on type mismatch instead of coercing.

    Returns:
        Tuple[Dict[str, Any], List[str]]: A tuple containing the normalized
                                          configuration and a list of warnings.
    """
    warnings: List[str] = []
    defaults = get_default_config()

    # 1. Base Type Validation
    if not isinstance(config, dict):
        msg = f"Invalid config type: expected dict, received {type(config).__name__}."
        if strict:
            raise TypeError(msg)
        warnings.append(f"{msg} Using defaults.")
        logger.warning(msg)
        return defaults, warnings

    # Initialize merged configuration with domain defaults
    merged: Dict[str, Any] = dict(defaults)
    merged.update(config)

    # 2. Schema Definition (Declarative mapping)
    string_fields = [
        "input_path", "output_base_dir", "output_subdir_name",
        "output_prefix", "target_model"
    ]

    bool_fields = [
        "process_modules", "process_tests", "process_resources",
        "create_individual_files", "create_unified_file",
        "show_functions", "show_classes", "show_methods",
        "generate_tree", "print_tree", "save_error_log", "respect_gitignore",
        "enable_sanitizer", "mask_user_paths", "minify_output"
    ]

    list_fields_map = {
        "extensions": default_extensions(),
        "include_patterns": default_include_patterns(),
        "exclude_patterns": default_exclude_patterns(),
    }

    # 3. Field Processing & Normalization
    for field in string_fields:
        merged[field] = _as_str(
            merged.get(field), defaults.get(field, ""), field, warnings, strict
        )

    for field in bool_fields:
        merged[field] = _as_bool(
            merged.get(field), defaults.get(field, False), field, warnings, strict
        )

    for field, fallback in list_fields_map.items():
        merged[field] = _as_list_str(
            merged.get(field), fallback, field, warnings, strict
        )

    # 4. Domain-Specific Normalization (Extensions)
    merged["extensions"] = _normalize_extensions(merged["extensions"], warnings, strict)

    return merged, warnings


# -----------------------------------------------------------------------------
# PRIVATE HELPERS: TYPE COERCION
# -----------------------------------------------------------------------------

def _as_str(value: Any, fallback: str, field: str, warnings: List[str], strict: bool) -> str:
    """Validate and sanitize string inputs."""
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip()
        return v if v else fallback

    msg = f"Invalid field '{field}': expected str, received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    return fallback


def _as_bool(value: Any, fallback: bool, field: str, warnings: List[str], strict: bool) -> bool:
    """Coerce various input types into native booleans."""
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback

    if not strict:
        # Support numeric coercion (0/1)
        if isinstance(value, (int, float)) and value in (0, 1):
            warnings.append(f"Field '{field}' converted from number {value} to bool.")
            return bool(value)
        # Support string coercion (human-friendly keywords)
        if isinstance(value, str):
            s = value.strip().lower()
            if s in ("true", "1", "yes", "y", "si", "sí"):
                warnings.append(f"Field '{field}' converted from '{value}' to True.")
                return True
            if s in ("false", "0", "no", "n"):
                warnings.append(f"Field '{field}' converted from '{value}' to False.")
                return False

    msg = f"Invalid field '{field}': expected bool, received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    return fallback


def _as_list_str(value: Any, fallback: List[str], field: str, warnings: List[str], strict: bool) -> List[str]:
    """Ensure input is a list of sanitized strings, supporting CSV parsing."""
    if value is None:
        return list(fallback)

    # Support CSV string to list conversion for CLI/GUI compatibility
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
                msg = f"Invalid item in '{field}[{i}]': expected str."
                if strict:
                    raise TypeError(msg)
                warnings.append(f"{msg} Item discarded.")
        return out if out else list(fallback)

    msg = f"Invalid field '{field}': expected list[str], received {type(value).__name__}."
    if strict:
        raise TypeError(msg)
    warnings.append(f"{msg} Using fallback.")
    return list(fallback)


# -----------------------------------------------------------------------------
# PRIVATE HELPERS: DOMAIN NORMALIZATION
# -----------------------------------------------------------------------------

def _normalize_extensions(exts: List[str], warnings: List[str], strict: bool) -> List[str]:
    """Ensure all file extensions are prefixed with a dot for filesystem consistency."""
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
    return out if out else default_extensions()