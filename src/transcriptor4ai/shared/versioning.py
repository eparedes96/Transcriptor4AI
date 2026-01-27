from __future__ import annotations

"""
Semantic Versioning Precedence Service.

Provides deterministic logic to evaluate application version precedence following 
the SemVer pattern. Centralizes version parsing and normalization to ensure 
consistency across update management and state migration components.
"""

import logging
from typing import Tuple

# Standardized logger for the shared utilities domain
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API: PRECEDENCE LOGIC
# ==============================================================================

def is_newer(current: str, latest: str) -> bool:
    """
    Evaluate if the latest version string has precedence over the current one.

    Implements a robust comparison that handles 'v' prefixes and discards
    non-numeric metadata for the primary comparison.

    Args:
        current: The version string of the running application.
        latest: The version string discovered from remote sources.

    Returns:
        bool: True if latest > current based on integer segment comparison.
    """
    # 1. VALIDATION: Quick exit if strings are identical or empty
    if not current or not latest or current.strip() == latest.strip():
        return False

    try:
        # 2. PROCESS: Transform raw strings into comparable numeric sequences
        current_tuple = _parse_version(current)
        latest_tuple = _parse_version(latest)

        # 3. COMPARISON: Leverage Python's lexical tuple comparison (segment by segment)
        return latest_tuple > current_tuple

    except (ValueError, TypeError, IndexError) as e:
        logger.warning(f"Versioning: Deterministic comparison failed for '{current}' vs '{latest}': {e}")
        return False


# ==============================================================================
# PRIVATE HELPERS: PARSING & NORMALIZATION
# ==============================================================================

def _parse_version(version_str: str) -> Tuple[int, ...]:
    """
    Convert a semantic version string into a comparable tuple of integers.

    Strips common prefixes and handles segments containing alphanumeric
    metadata (e.g., '2.1.0-beta' -> (2, 1, 0)).

    Args:
        version_str: Raw version identifier.

    Returns:
        Tuple[int, ...]: Sequence representing (Major, Minor, Patch, ...).
    """
    # 1. CLEAN: Remove 'v' prefix and whitespace, then segment by period
    clean_str = version_str.lower().lstrip("v").strip()
    parts = clean_str.split(".")

    numeric_parts: list[int] = []

    # 2. EXTRACT: Isolate numeric values from each segment
    for p in parts:
        # Filter only digits from the segment to handle pre-release suffixes
        digit_str = "".join(filter(str.isdigit, p))

        # Fallback to 0 if the segment contains no digits to prevent ValueError
        numeric_parts.append(int(digit_str) if digit_str else 0)

    # 3. CONFORM: Ensure at least Major.Minor.Patch structure exists
    # Append trailing zeros to prevent tuple length mismatch in comparison
    while len(numeric_parts) < 3:
        numeric_parts.append(0)

    return tuple(numeric_parts)