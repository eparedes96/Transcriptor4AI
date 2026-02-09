from __future__ import annotations

# ==============================================================================
# TEST GROUP: AST PARSER SERVICE (UNIT)
# ==============================================================================

import pytest
from pathlib import Path
from transcriptor4ai.application.analysis.ast_parser import extract_definitions

@pytest.fixture
def calculator_file_path(sample_project_source: Path) -> Path:
    """
    Returns the path to the real calculator.py in the test data folder.
    """
    return sample_project_source / "src" / "calculator.py"


@pytest.mark.unit
def test_extract_definitions_happy_path(calculator_file_path):
    """
    Verifies full extraction of classes, methods and functions using
    the real 'calculator.py' source file.
    """
    # 1. ARRANGE: Done by fixture

    # 2. ACT: Extract all available symbols
    results = extract_definitions(
        calculator_file_path,
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    # 3. ASSERT: Verify real symbols from tests/data/sample_project/src/calculator.py
    assert "Class: Calculator" in results
    assert "  Method: __init__()" in results
    assert "  Method: add()" in results
    assert "  Method: _internal_reset()" in results
    assert "Function: standalone_function()" in results
    assert len(results) == 5


@pytest.mark.unit
def test_extract_definitions_respects_visibility_filters(calculator_file_path):
    """
    Ensures that disabling specific flags (like show_methods or show_classes)
    correctly prunes the resulting list from a real file.
    """
    # 1. ARRANGE: Configure filters to hide methods
    # 2. ACT
    results = extract_definitions(
        calculator_file_path,
        show_functions=True,
        show_classes=True,
        show_methods=False
    )

    # 3. ASSERT: Methods should be absent
    assert "Class: Calculator" in results
    assert "Function: standalone_function()" in results
    assert "  Method: add()" not in results
    assert len(results) == 2


@pytest.mark.unit
def test_extract_definitions_handles_syntax_error(tmp_path):
    """
    Verifies that the service handles malformed Python code gracefully
    by returning a diagnostic message instead of crashing.
    """
    # 1. ARRANGE: Create a file with broken syntax (Missing colon)
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def missing_colon()", encoding="utf-8")

    # 2. ACT
    results = extract_definitions(broken_file, True, True, True)

    # 3. ASSERT: Should return an error descriptor string
    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "SyntaxError" in results[0]


@pytest.mark.unit
def test_extract_definitions_missing_file(tmp_path):
    """
    Ensures that providing a non-existent path returns a
    descriptive error message instead of an OS exception.
    """
    # 1. ARRANGE: Target a path that definitely does not exist
    fake_file = tmp_path / "ghost_file.py"

    # 2. ACT
    results = extract_definitions(fake_file, True, True)

    # 3. ASSERT
    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "Could not read" in results[0]


@pytest.mark.unit
def test_extract_definitions_empty_file(tmp_path):
    """
    An empty file should result in an empty list of definitions.
    """
    # 1. ARRANGE: Create an empty file
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("", encoding="utf-8")

    # 2. ACT
    results = extract_definitions(empty_file, True, True)

    # 3. ASSERT
    assert results == []


@pytest.mark.unit
def test_extract_definitions_resilience_to_binary_content(tmp_path):
    """
    Verify that attempting to parse a corrupted file (binary) is caught.
    We use pure null bytes to ensure a SyntaxError even with 'replace' decoding.
    """
    # 1. ARRANGE: Write raw binary that is definitively not parseable as Python
    bin_file = tmp_path / "binary_junk.py"
    bin_file.write_bytes(b"\x00\x00\x00\x00\x00")

    # 2. ACT
    results = extract_definitions(bin_file, True, True)

    # 3. ASSERT
    # Must return 1 entry containing the error descriptor
    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "SyntaxError" in results[0]