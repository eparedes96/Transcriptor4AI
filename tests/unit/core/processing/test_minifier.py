from __future__ import annotations

"""
Unit tests for the Minification utility.

Ensures that comments and excessive whitespace are removed across
different programming languages while preserving logical code structure.
"""

import pytest
from transcriptor4ai.core.processing.minifier import minify_code, minify_code_stream


def test_minify_code_python_comments():
    """Verify removal of Python-style comments (#)."""
    code = """
def main():
    # This is a comment
    print("Hello") # Inline comment
    """
    minified = minify_code(code, ".py")

    assert "# This is a comment" not in minified
    assert "def main():" in minified
    assert 'print("Hello")' in minified
    assert "# Inline comment" not in minified


def test_minify_code_c_style_comments():
    """Verify removal of C-style comments (//) for relevant languages."""
    code = """
// Header comment
function init() {
    let x = 10; // set x
}
    """

    # Test JS
    minified_js = minify_code(code, ".js")
    assert "Header comment" not in minified_js
    assert "// set x" not in minified_js
    assert "function init()" in minified_js

    # Test Java
    minified_java = minify_code(code, ".java")
    assert "Header comment" not in minified_java
    assert "function init()" in minified_java


def test_minify_code_collapses_newlines():
    """Ensure that multiple blank lines are reduced to a maximum of one/two."""
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


def test_minify_code_trims_whitespace():
    """Verify trailing whitespace removal."""
    code = "  def func():    \n    pass    "
    minified = minify_code(code, ".py")

    # Expect: "  def func():\n    pass" (leading indentation kept, trailing removed)
    assert minified == "  def func():\n    pass"


def test_minify_code_handles_empty_input():
    """Ensure resilience against empty or None input."""
    assert minify_code("", ".py") == ""
    assert minify_code(None, ".py") == ""


def test_minify_stream_logic():
    """Test the generator function directly."""
    lines = ["line1\n", "\n", "\n", "line2\n"]
    result = list(minify_code_stream(iter(lines), ".py"))

    # Should collapse the two middle newlines into one
    assert len(result) == 3
    assert result[0] == "line1\n"
    assert result[1] == "\n"
    assert result[2] == "line2\n"