from __future__ import annotations

# ==============================================================================
# TEST GROUP: FORMATTING OPTIONS (VALUE OBJECTS)
# ==============================================================================

import pytest

from transcriptor4ai.domain.entities.formatting_options import OutputFormat, ContextSection


def test_output_format_enum_members_should_match_specification():
    """
    Verifies that the core output formats required for v2.2 are
    defined in the enumeration.
    """
    # 1. ARRANGE & 2. ACT: Direct access to Enum members
    # 3. ASSERT: Match against the polymorphic requirements
    assert OutputFormat.PLAIN_TEXT.value == "plaintext"
    assert OutputFormat.MARKDOWN.value == "markdown"
    assert OutputFormat.XML.value == "xml"


def test_list_values_should_return_all_supported_strings():
    """
    Ensures that the helper method returns a clean list of string values
    for the GUI/CLI to consume.
    """
    # 1. ARRANGE
    expected = ["plaintext", "markdown", "xml"]

    # 2. ACT
    values = OutputFormat.list_values()

    # 3. ASSERT
    # Order should be preserved according to Enum definition
    assert values == expected


@pytest.mark.parametrize("input_str, expected_enum", [
    ("plaintext", OutputFormat.PLAIN_TEXT),
    ("  markdown  ", OutputFormat.MARKDOWN),  # Whitespace resilience
    ("XML", OutputFormat.XML),  # Case insensitivity
    ("Markdown", OutputFormat.MARKDOWN),  # Mixed case
])
def test_from_str_should_resolve_valid_inputs_correctly(input_str, expected_enum):
    """
    Validates the robust factory method for instantiating OutputFormat from strings.
    """
    # 1. ARRANGE & 2. ACT
    result = OutputFormat.from_str(input_str)

    # 3. ASSERT
    assert result == expected_enum


def test_from_str_should_return_fallback_on_unrecognized_input():
    """
    Ensures the system fails safely by returning PLAIN_TEXT if an
    unsupported format string is provided.
    """
    # 1. ARRANGE
    garbage_input = "yaml_or_something_unsupported"

    # 2. ACT
    result = OutputFormat.from_str(garbage_input)

    # 3. ASSERT
    # Standard fallback to ensure the pipeline doesn't crash
    assert result == OutputFormat.PLAIN_TEXT


def test_from_str_should_respect_custom_fallback():
    """
    Verifies that the safe factory accepts a custom fallback
    for specific validation scenarios.
    """
    # 1. ARRANGE
    invalid_input = "unknown"
    custom_fallback = OutputFormat.XML

    # 2. ACT
    result = OutputFormat.from_str(invalid_input, fallback=custom_fallback)

    # 3. ASSERT
    assert result == OutputFormat.XML


def test_context_sections_should_cover_all_artifact_types():
    """
    Verifies that the ContextSection enumeration contains all
    semantic markers used by the Assembler.
    """
    # 1. ARRANGE & 2. ACT: Retrieve enum names
    names = [s.name for s in ContextSection]

    # 3. ASSERT: Ensure parity with business categories
    assert "PREAMBLE" in names
    assert "TREE" in names
    assert "MODULES" in names
    assert "TESTS" in names
    assert "RESOURCES" in names