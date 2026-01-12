from __future__ import annotations

"""
Unit tests for the AST Parser service.

Verifies the extraction of classes, functions, and methods from Python source code.
Ensures robustness against syntax errors and empty files.
"""

import pytest
from transcriptor4ai.core.analysis.ast_parser import extract_definitions


def test_extract_definitions_finds_classes_and_functions(tmp_path):
    """
    Verify that the AST parser correctly identifies classes, functions, and methods.
    """
    content = """
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
"""
    f = tmp_path / "dummy.py"
    f.write_text(content, encoding="utf-8")

    results = extract_definitions(
        str(f),
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    assert "Class: MyClass" in results
    assert "Function: my_function()" in results
    # Check for method presence (indentation/formatting might vary, so check substring)
    assert any("Method: my_method()" in r for r in results)


def test_extract_definitions_handles_syntax_error(tmp_path):
    """
    The parser should not crash on invalid python code.
    It should return a descriptive error message in the list.
    """
    f = tmp_path / "broken.py"
    f.write_text("def broken_code( :", encoding="utf-8")

    results = extract_definitions(str(f), True, True)

    assert len(results) == 1
    assert "[ERROR]" in results[0]
    assert "SyntaxError" in results[0]


def test_extract_definitions_filters_elements(tmp_path):
    """
    Verify that flags (show_functions, show_classes) effectively filter the output.
    """
    content = """
class HiddenClass:
    pass

def visible_function():
    pass
"""
    f = tmp_path / "filter.py"
    f.write_text(content, encoding="utf-8")

    results = extract_definitions(
        str(f),
        show_functions=True,
        show_classes=False
    )

    assert "Function: visible_function()" in results
    assert "Class: HiddenClass" not in results


def test_extract_definitions_handles_empty_file(tmp_path):
    """An empty file should return an empty list, not crash."""
    f = tmp_path / "empty.py"
    f.write_text("", encoding="utf-8")

    results = extract_definitions(str(f), True, True)
    assert results == []


def test_extract_definitions_handles_missing_file():
    """Passing a non-existent path should return an error message."""
    results = extract_definitions("/non/existent/path.py", True, True)

    assert len(results) == 1
    assert "[ERROR]" in results[0]