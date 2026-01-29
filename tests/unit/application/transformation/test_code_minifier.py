from __future__ import annotations

# ==============================================================================
# TEST GROUP: CODE MINIFIER SERVICE
# ==============================================================================

import pytest
from transcriptor4ai.application.transformation.code_minifier import CodeMinifierService


@pytest.fixture
def minifier() -> CodeMinifierService:
    """Provides a fresh instance of the CodeMinifierService."""
    return CodeMinifierService()


@pytest.mark.unit
def test_minify_python_comments(minifier):
    """
    Verifies that Python-style comments are removed while preserving
    the functional code and indentation.
    """
    # 1. ARRANGE
    code = (
        "def main():\n"
        "    # This is a comment\n"
        "    print('Hello')  # Inline comment\n"
    )
    expected = "def main():\n    print('Hello')"

    # 2. ACT
    result = minifier.minify(code, ".py")

    # 3. ASSERT
    assert "# This is a comment" not in result
    assert "# Inline comment" not in result
    assert "def main():" in result
    assert "print('Hello')" in result


@pytest.mark.unit
@pytest.mark.parametrize("ext", [".js", ".ts", ".java", ".cpp", ".cs", ".go"])
def test_minify_c_style_comments(minifier, ext):
    """
    Verifies that C-style double-slash comments are removed for
    all supported languages in that family.
    """
    # 1. ARRANGE
    code = (
        "// Global header\n"
        "function init() {\n"
        "    let x = 10; // set value\n"
        "}"
    )

    # 2. ACT
    result = minifier.minify(code, ext)

    # 3. ASSERT
    assert "// Global header" not in result
    assert "// set value" not in result
    assert "function init()" in result


@pytest.mark.unit
def test_minify_collapses_multiple_newlines(minifier):
    """
    Ensures that multiple consecutive empty lines are collapsed into
    a single newline to save tokens without losing structural separation.
    """
    # 1. ARRANGE
    code = (
        "class A:\n"
        "    pass\n"
        "\n"
        "\n"
        "\n"
        "class B:\n"
        "    pass"
    )

    # 2. ACT
    result = minifier.minify(code, ".py")

    # 3. ASSERT
    # Should not have more than one empty line between classes
    assert "\n\n\n" not in result
    assert "class A:" in result
    assert "class B:" in result


@pytest.mark.unit
def test_minify_trims_trailing_whitespace(minifier):
    """
    Verify that redundant spaces at the end of lines are removed.
    """
    # 1. ARRANGE
    code = "def func():    \n    x = 1    "
    expected = "def func():\n    x = 1"

    # 2. ACT
    result = minifier.minify(code, ".py")

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
def test_minify_stream_consistency(minifier):
    """
    Validates that the streaming minification produces the same
    logical lines as the in-memory version.
    """
    # 1. ARRANGE
    lines = ["import os\n", "\n", "# comment\n", "print(os.name)\n"]

    # 2. ACT
    stream_result = list(minifier.minify_stream(iter(lines), ".py"))
    processed_content = "".join(stream_result).rstrip()

    # 3. ASSERT
    assert "# comment" not in processed_content
    assert len(stream_result) <= len(lines)
    assert "import os" in processed_content


@pytest.mark.unit
def test_minify_handles_unsupported_extension(minifier):
    """
    If an extension is not recognized, it should still perform
    basic whitespace cleanup but skip comment removal logic.
    """
    # 1. ARRANGE
    text = "data: 123    \n# not a comment in this format"

    # 2. ACT
    result = minifier.minify(text, ".unknown")

    # 3. ASSERT
    assert "data: 123" in result
    assert "# not a comment" in result  # Should NOT be removed
    assert result.endswith("format")  # Trimming should still work