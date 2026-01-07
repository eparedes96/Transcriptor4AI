from __future__ import annotations

"""
Configuration validation and normalization gatekeeper.

This module ensures that all input data follows the expected types and formats 
before reaching the business logic, acting as the primary security layer for 
the pipeline.
"""

import logging
from typing import Any, Dict, List, Tuple

from transcriptor4ai.config import get_default_config
from transcriptor4ai.filtering import (
    default_extensions,
    default_include_patterns,
    default_exclude_patterns,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
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
    defaults = get_default_config()

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
    merged["input_path"] = _as_str(
        merged.get("input_path"),
        defaults["input_path"],
        "input_path",
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

    # 3. Content Selection & Output Format (Booleans)
    merged["process_modules"] = _as_bool(
        merged.get("process_modules"),
        defaults["process_modules"],
        "process_modules",
        warnings,
        strict
    )
    merged["process_tests"] = _as_bool(
        merged.get("process_tests"),
        defaults["process_tests"],
        "process_tests",
        warnings,
        strict
    )
    merged["process_resources"] = _as_bool(
        merged.get("process_resources"),
        defaults["process_resources"],
        "process_resources",
        warnings,
        strict
    )

    merged["create_individual_files"] = _as_bool(
        merged.get("create_individual_files"),
        defaults["create_individual_files"],
        "create_individual_files",
        warnings,
        strict
    )
    merged["create_unified_file"] = _as_bool(
        merged.get("create_unified_file"),
        defaults["create_unified_file"],
        "create_unified_file",
        warnings,
        strict
    )

    # 4. Feature Flags (AST & Logging & Filtering)
    merged["show_functions"] = _as_bool(
        merged.get("show_functions"),
        defaults["show_functions"],
        "show_functions",
        warnings,
        strict
    )
    merged["show_classes"] = _as_bool(
        merged.get("show_classes"),
        defaults["show_classes"],
        "show_classes",
        warnings,
        strict
    )
    merged["show_methods"] = _as_bool(
        merged.get("show_methods"),
        defaults["show_methods"],
        "show_methods",
        warnings,
        strict
    )

    merged["generate_tree"] = _as_bool(
        merged.get("generate_tree"),
        defaults["generate_tree"],
        "generate_tree",
        warnings,
        strict
    )
    merged["print_tree"] = _as_bool(
        merged.get("print_tree"),
        defaults["print_tree"],
        "print_tree",
        warnings,
        strict
    )
    merged["save_error_log"] = _as_bool(
        merged.get("save_error_log"),
        defaults["save_error_log"],
        "save_error_log",
        warnings,
        strict
    )
    merged["respect_gitignore"] = _as_bool(
        merged.get("respect_gitignore"),
        defaults["respect_gitignore"],
        "respect_gitignore",
        warnings,
        strict
    )

    # 5. Lists Normalization: Extensions and Patterns
    merged["extensions"] = _as_list_str(
        merged.get("extensions"),
        default_extensions(),
        "extensions",
        warnings,
        strict,
    )
    merged["extensions"] = _normalize_extensions(merged["extensions"], warnings, strict)

    merged["include_patterns"] = _as_list_str(
        merged.get("include_patterns"),
        default_include_patterns(),
        "include_patterns",
        warnings,
        strict,
    )
    merged["exclude_patterns"] = _as_list_str(
        merged.get("exclude_patterns"),
        default_exclude_patterns(),
        "exclude_patterns",
        warnings,
        strict,
    )

    return merged, warnings


# -----------------------------------------------------------------------------
# Internal Helpers (Private)
# -----------------------------------------------------------------------------
def _as_str(value: Any, fallback: str, field: str, warnings: List[str], strict: bool) -> str:
    """Ensure the value is a non-empty string or use fallback."""
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
    """Coerce various input types into a boolean value."""
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
    """Ensure the value is a list of strings, handles CSV strings in non-strict mode."""
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


def _normalize_extensions(exts: List[str], warnings: List[str], strict: bool) -> List[str]:
    """Ensure all extensions start with a dot."""
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