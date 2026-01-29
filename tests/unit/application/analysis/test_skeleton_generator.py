from __future__ import annotations

# ==============================================================================
# TEST GROUP: SKELETON GENERATOR LOGIC
# ==============================================================================

import pytest
from transcriptor4ai.application.analysis.ast_parser import generate_skeleton_code


@pytest.mark.unit
def test_generate_skeleton_strips_function_bodies():
    """
    Verifies that implementation logic inside functions is replaced
    by 'pass' while keeping the signature.
    """
    # 1. ARRANGE
    source = (
        "def heavy_computation(x: int, y: int) -> int:\n"
        "    result = x * y\n"
        "    for i in range(10):\n"
        "        result += i\n"
        "    return result"
    )
    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert "def heavy_computation(x: int, y: int) -> int:" in result
    assert "pass" in result
    assert "result = x * y" not in result
    assert "for i in range(10):" not in result


@pytest.mark.unit
def test_generate_skeleton_preserves_docstrings():
    """
    Docstrings are high-value context for LLMs. This test ensures they
    are kept above the 'pass' statement.
    """
    # 1. ARRANGE
    source = (
        "def api_call():\n"
        "    \"\"\"Performs a secure request.\"\"\"\n"
        "    do_magic()\n"
        "    return 200"
    )

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert '"""Performs a secure request."""' in result
    assert "pass" in result
    assert "do_magic()" not in result


@pytest.mark.unit
def test_generate_skeleton_preserves_decorators_and_async():
    """
    Verifies that async definitions and decorators remain intact
    as they define how the code is executed.
    """
    # 1. ARRANGE
    source = (
        "@app.route('/')\n"
        "async def index():\n"
        "    return await render_template('index.html')"
    )

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert "@app.route('/')" in result
    assert "async def index():" in result
    assert "pass" in result


@pytest.mark.unit
def test_generate_skeleton_handles_classes_recursively():
    """
    Ensures nested methods within classes are also skeletonized.
    """
    # 1. ARRANGE
    source = (
        "class Controller:\n"
        "    def run(self):\n"
        "        self.setup()\n"
        "        self.execute()"
    )

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert "class Controller:" in result
    assert "def run(self):" in result
    assert "pass" in result
    assert "self.setup()" not in result


@pytest.mark.unit
def test_generate_skeleton_removes_top_level_logic():
    """
    To minimize token usage, non-definition code (like global variables
    or imports) should be pruned in skeleton mode.
    """
    # 1. ARRANGE
    source = (
        "import os\n"
        "VERSION = '1.0'\n"
        "def main(): pass"
    )

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert "def main():" in result
    assert "import os" not in result
    assert "VERSION =" not in result


@pytest.mark.unit
def test_generate_skeleton_handles_syntax_error_gracefully():
    """
    If the input code is not valid Python, the service should return
    a diagnostic message instead of raising an exception.
    """
    # 1. ARRANGE: Missing closing parenthesis
    source = "def broken_code(a, b:"

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT
    assert "[SKIPPING SKELETON]" in result
    assert "SyntaxError" in result


@pytest.mark.unit
def test_generate_skeleton_handles_empty_input():
    """
    Edge case: Empty string or whitespace should result in an empty skeleton.
    """
    # 2. ACT & 3. ASSERT
    assert generate_skeleton_code("") == ""
    assert generate_skeleton_code("   \n   ") == ""