from __future__ import annotations

# ==============================================================================
# TEST GROUP: AST PARSER SERVICE
# ==============================================================================

import pytest
from pathlib import Path
from transcriptor4ai.application.analysis.ast_parser import extract_definitions

@pytest.fixture
def complex_python_file(tmp_path: Path) -> Path:
    """
    Generates a sample Python file with classes, functions, and async methods.
    """
    content = (
        "import os\n\n"
        "class DataManager:\n"
        "    def __init__(self): pass\n"
        "    async def save_data(self): pass\n\n"
        "def top_level_func():\n"
        "    return True\n\n"
        "async def async_worker():\n"
        "    await save_data()"
    )
    file_path = tmp_path / "analyzer_target.py"
    file_path.write_text(content, encoding="utf-8")
    return file_path


@pytest.mark.unit
def test_extract_definitions_happy_path(complex_python_file):
    """
    Verifies full extraction of classes, methods and functions
    including async variants.
    """
    # 2. ACT
    results = extract_definitions(
        complex_python_file,
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    # 3. ASSERT
    assert "Class: DataManager" in results
    assert "  Method: __init__()" in results
    assert "  Method: save_data()" in results
    assert "Function: top_level_func()" in results
    assert "Function: async_worker()" in results
    assert len(results) == 5


@pytest.mark.unit
def test_extract_definitions_respects_visibility_filters(complex_python_file):
    """
    Ensures that disabling specific flags (like show_methods or show_classes)
    correctly prunes the resulting list.
    """
    # 1. ARRANGE: Only show classes, hide their methods and top-level functions
    # 2. ACT
    results = extract_definitions(
        complex_python_file,
        show_functions=False,
        show_classes=True,
        show_methods=False
    )

    # 3. ASSERT
    assert "Class: DataManager" in results
    assert "  Method: save_data()" not in results
    assert "Function: top_level_func()" not in results
    assert len(results) == 1


@pytest.mark.unit
def test_extract_definitions_handles_syntax_error(tmp_path):
    """
    Verifies that the service handles malformed Python code gracefully
    by returning a diagnostic message instead of crashing.
    """
    # 1. ARRANGE: Create a file with broken syntax
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def missing_colon()", encoding="utf-8")

    # 2. ACT
    results = extract_definitions(broken_file, True, True, True)

    # 3. ASSERT
    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "SyntaxError" in results[0]


@pytest.mark.unit
def test_extract_definitions_missing_file():
    """
    Ensures that providing a non-existent path returns a
    descriptive error message.
    """
    # 2. ACT
    results = extract_definitions("/non/existent/path.py", True, True)

    # 3. ASSERT
    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "Could not read" in results[0]


@pytest.mark.unit
def test_extract_definitions_empty_file(tmp_path):
    """
    An empty file should result in an empty list of definitions.
    """
    # 1. ARRANGE
    empty_file = tmp_path / "empty.py"
    empty_file.write_text("", encoding="utf-8")

    # 2. ACT
    results = extract_definitions(empty_file, True, True)

    # 3. ASSERT
    assert results == []


@pytest.mark.unit
def test_extract_definitions_resilience_to_binary_content(tmp_path):
    """
    Verify that attempting to parse a non-text or corrupted file
    is caught by the I/O error handling.
    """
    # 1. ARRANGE: Write raw binary that is not valid UTF-8
    bin_file = tmp_path / "binary.py"
    bin_file.write_bytes(b"\x80\x81\xfe\xff")

    # 2. ACT
    results = extract_definitions(bin_file, True, True)

    # 3. ASSERT
    assert len(results) == 1
    assert "[ERROR]" in results[0]