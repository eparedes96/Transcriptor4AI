from __future__ import annotations

"""
Unit tests for Semantic Versioning logic.

Validates that the application can correctly identify update availability 
by comparing version strings with different formats and metadata.
"""

import pytest
from transcriptor4ai.shared.versioning import is_newer, _parse_version


# ==============================================================================
# TEST GROUP: VERSION PARSING LOGIC
# ==============================================================================

@pytest.mark.parametrize("input_str, expected_tuple", [
    ("2.1.0", (2, 1, 0)),
    ("v2.1.0", (2, 1, 0)),  # Strips 'v' prefix
    ("2.1", (2, 1, 0)),  # Pads missing segments
    ("2", (2, 0, 0)),  # Extreme padding
    ("2.1.0-beta", (2, 1, 0)),  # Discards non-numeric suffixes
    ("  v3.4.5  ", (3, 4, 5)),  # Handles whitespace
    ("invalid", (0, 0, 0)),  # Fallback for non-numeric
])
def test_parse_version_normalizes_various_formats(input_str, expected_tuple):
    """
    Ensures that version strings are consistently transformed into
    comparable integer tuples.
    """
    # 1. ARRANGE & 2. ACT
    result = _parse_version(input_str)

    # 3. ASSERT
    assert result == expected_tuple


# ==============================================================================
# TEST GROUP: VERSION COMPARISON (IS_NEWER)
# ==============================================================================

@pytest.mark.parametrize("current, latest, expected_result", [
    # Patch updates
    ("2.1.0", "2.1.1", True),
    ("2.1.1", "2.1.0", False),

    # Minor updates
    ("2.1.9", "2.2.0", True),
    ("2.2.0", "2.1.9", False),

    # Major updates
    ("1.9.9", "2.0.0", True),

    # Identity & Equality
    ("2.1.0", "2.1.0", False),  # Same version is not 'newer'
    ("v2.1.0", "2.1.0", False),  # Prefixes don't change equality

    # Short vs Long formats
    ("2.1", "2.1.1", True),  # 2.1.0 < 2.1.1
    ("2.1.1", "2.2", True),  # 2.1.1 < 2.2.0

    # Metadata handling (SUT logic ignores beta/alpha tags)
    ("2.1.0", "2.1.0-beta", False),  # Treated as 2.1.0 == 2.1.0
])
def test_is_newer_correctly_evaluates_precedence(current, latest, expected_result):
    """
    Verifies the boolean outcome of the version comparison
    across different update scenarios.
    """
    # 1. ARRANGE & 2. ACT
    result = is_newer(current, latest)

    # 3. ASSERT
    assert result is expected_result


# ==============================================================================
# TEST GROUP: RESILIENCE & ERROR HANDLING
# ==============================================================================

@pytest.mark.parametrize("bad_current, bad_latest", [
    (None, "2.1.0"),
    ("2.1.0", None),
    ("", "2.1.0"),
    ("2.1.0", ""),
    ("  ", "  "),
])
def test_is_newer_is_resilient_to_null_or_empty_inputs(bad_current, bad_latest):
    """
    Prevents the application from crashing if the remote API returns
    empty strings or if the local version is missing.
    """
    # 1. ARRANGE & 2. ACT
    # The function should return False gracefully instead of raising Exceptions
    result = is_newer(bad_current, bad_latest)

    # 3. ASSERT
    assert result is False