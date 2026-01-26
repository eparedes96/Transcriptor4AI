from __future__ import annotations

"""
Data Conversion and Sanitization Utilities.

Provides reusable functions for type coercion and data normalization. 
Specifically designed to handle untrusted inputs from CLI arguments 
and GUI form fields, transforming them into strictly typed domain values.
"""

import logging
from typing import Any, List

# Standard logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PRIMITIVE CONVERTERS
# ==============================================================================

def to_str(value: Any, fallback: str = "") -> str:
    """
    Sanitize and ensure a value is a valid string.

    Args:
        value: Input of any type.
        fallback: Value to return if input is null or invalid.

    Returns:
        str: Trimmed string or fallback.
    """
    if value is None:
        return fallback

    if isinstance(value, str):
        # 1. PROCESS: Remove surrounding whitespace
        v = value.strip()
        return v if v else fallback

    return str(value).strip()


def scrub_bool(value: Any, fallback: bool = False, *, strict: bool = False) -> bool:
    """
    Coerce human-friendly inputs into native Booleans.

    Supports:
    - Booleans: True/False
    - Numbers: 0/1
    - Strings: 'true', 'false', 'yes', 'no', 'y', 'n', 'si', '1', '0'

    Args:
        value: Input to convert.
        fallback: Default value on failure.
        strict: If True, raises TypeError on type mismatch instead of coercing.

    Returns:
        bool: Coerced boolean value.
    """
    if isinstance(value, bool):
        return value

    if value is None:
        return fallback

    # 1. VALIDATION: Handle strict mode enforcement
    if strict and not isinstance(value, (bool, int, str)):
        raise TypeError(f"Cannot coerce {type(value).__name__} to bool in strict mode.")

    # 2. PROCESS: Numeric coercion (0/1)
    if isinstance(value, (int, float)) and value in (0, 1):
        return bool(value)

    # 3. PROCESS: String keyword mapping
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("true", "1", "yes", "y", "si", "sí", "on"):
            return True
        if s in ("false", "0", "no", "n", "off"):
            return False

    return fallback


# ==============================================================================
# COLLECTION CONVERTERS
# ==============================================================================

def to_list_str(value: Any, fallback: List[str] | None = None) -> List[str]:
    """
    Transform inputs into a list of sanitized strings.
    Supports CSV parsing for string inputs.

    Args:
        value: String (CSV), List, or None.
        fallback: Default list if input is invalid.

    Returns:
        List[str]: Cleaned list of strings.
    """
    if fallback is None:
        fallback = []

    if value is None:
        return list(fallback)

    # 1. PROCESS: CSV String parsing
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",") if x.strip()]
        return items if items else list(fallback)

    # 2. PROCESS: List cleaning
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            s = str(item).strip()
            if s:
                out.append(s)
        return out if out else list(fallback)

    return list(fallback)


# ==============================================================================
# DOMAIN-SPECIFIC NORMALIZERS
# ==============================================================================

def normalize_extension(ext: str) -> str:
    """
    Ensure a file extension is correctly formatted with a leading dot.

    Args:
        ext: Raw extension string (e.g., 'py', '.js').

    Returns:
        str: Normalized extension (e.g., '.py', '.js').
    """
    # 1. CLEAN: Remove whitespace and leading artifacts
    e = ext.strip().lower()
    if not e:
        return ""

    # 2. FORMAT: Add dot if missing
    if not e.startswith("."):
        return f".{e}"

    return e