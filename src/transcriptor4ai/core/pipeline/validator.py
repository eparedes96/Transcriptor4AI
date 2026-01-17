from __future__ import annotations

"""
Configuration Validator.

Acts as a gatekeeper to ensure that the configuration dictionary passed
to the pipeline contains valid types and normalized values.
Uses a schema-driven approach to minimize boilerplate.
"""

import logging
from typing import Any, Dict, List, Tuple, Callable

from transcriptor4ai.core.pipeline.filters import (
    default_extensions,
    default_include_patterns,
    default_exclude_patterns,
)
from transcriptor4ai.domain.config import get_default_config

logger = logging.getLogger(__name__)


def validate_config(
        config: Any,
        *,
        strict: bool = False,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Validate and normalize the configuration dictionary.

    Ensures types are correct (converting strings to bools/lists if needed)
    and fills in missing values with defaults using a declarative schema.

    Args:
        config: The raw configuration dictionary (or untrusted input).
        strict: If True, raises TypeError/ValueError on invalid data.

    Returns:
        Tuple[Dict, List[str]]: (Normalized Config, List of Warnings).
    """
    warnings: List[str] = []
    defaults = get_default_config()

    # Base Validation: Type Check
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

    # Declarative Schema Definition
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

    # Process String Fields
    for field in string_fields:
        merged[field] = _as_str(
            merged.get(field), defaults.get(field, ""), field, warnings, strict
        )

    # Process Boolean Fields
    for field in bool_fields:
        merged[field] = _as_bool(
            merged.get(field), defaults.get(field, False), field, warnings, strict
        )

    # Process List Fields
    for field, fallback in list_fields_map.items():
        merged[field] = _as_list_str(
            merged.get(field), fallback, field, warnings, strict
        )

    # Post-processing normalization
    merged["extensions"] = _normalize_extensions(merged["extensions"], warnings, strict)

    return merged, warnings


def _as_str(value: Any, fallback: str, field: str, warnings: List[str], strict: bool) -> str:
    """Ensure value is a string."""
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
    """Coerce value to boolean."""
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
    """Ensure value is a list of strings."""
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


def _normalize_extensions(exts: List[str], warnings: List[str], strict: bool) -> List[str]:
    """Ensure extensions start with a dot."""
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