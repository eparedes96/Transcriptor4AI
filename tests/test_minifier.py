from __future__ import annotations

"""
Unit tests for the Minification utility.

Ensures that comments and excessive whitespace are removed across
different programming languages while preserving logical code structure.
"""

import pytest
from transcriptor4ai.utils.minify_code import minify_code


def test_minify_code_python_comments() -> None:
    """Verify removal of Python-style comments (#)."""
    code = """
# This is a comment
def main():
    print("Hello")  # Inline comment
    """
    minified = minify_code(code, ".py")

    assert "This is a comment" not in minified
    assert "# Inline comment" not in minified
    assert "def main():" in minified
    assert 'print("Hello")' in minified


def test_minify_code_c_style_comments() -> None:
    """Verify removal of C-style comments (//) for relevant languages."""
    code = """
// Header comment
function init() {
    let x = 10; // set x
}
    """
    # Test for JS
    minified_js = minify_code(code, ".js")
    assert "Header comment" not in minified_js
    assert "// set x" not in minified_js
    assert "function init()" in minified_js

    # Test for Java
    minified_java = minify_code(code, ".java")
    assert "Header comment" not in minified_java
    assert "function init()" in minified_java


def test_minify_code_collapses_newlines() -> None:
    """Ensure that multiple blank lines are reduced to a maximum of two."""
    code = """
class A:
    pass



class B:
    pass
    """
    minified = minify_code(code, ".py")

    assert "\n\n\n" not in minified
    assert "class A:" in minified
    assert "class B:" in minified


def test_minify_code_trims_whitespace() -> None:
    """Verify trailing whitespace removal and overall trimming."""
    code = "  def func():    \n    pass    "
    minified = minify_code(code, ".py")

    assert minified == "def func():\n    pass"


def test_minify_code_handles_empty_input() -> None:
    """Ensure resilience against empty or None input."""
    assert minify_code("", ".py") == ""
    assert minify_code(None, ".py") == ""  # type: ignore