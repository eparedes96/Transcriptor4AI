from __future__ import annotations

from pathlib import Path

# ==============================================================================
# TEST GROUP: SKELETON GENERATOR LOGIC (UNIT)
# ==============================================================================
import pytest

from transcriptor4ai.application.analysis.ast_parser import generate_skeleton_code


@pytest.fixture
def calculator_source(sample_project_source: Path) -> str:
    """
    Loads the raw content of the real calculator.py for transformation tests.
    """
    # Ensures we are testing against a physical file with real Python syntax
    file_path = sample_project_source / "src" / "calculator.py"
    return file_path.read_text(encoding="utf-8")


@pytest.mark.unit
def test_generate_skeleton_strips_function_bodies_from_real_file(calculator_source):
    """
    Verifies that implementation logic inside the 'add' method of the
    real Calculator class is replaced by 'pass'.
    """
    # 1. ARRANGE: calculator_source contains 'self.value += number'

    # 2. ACT: Process source code through the AST transformer
    result = generate_skeleton_code(calculator_source)

    # 3. ASSERT: Method signature remains but body is neutralized
    assert "def add(self, number: int) -> int:" in result
    assert "pass" in result
    assert "self.value += number" not in result
    assert "def standalone_function():" in result


@pytest.mark.unit
def test_generate_skeleton_preserves_docstrings_from_real_file(calculator_source):
    """
    Docstrings are high-value context for LLMs. This test ensures the
    real docstrings in 'calculator.py' are kept in the skeleton.
    """
    # 1. ARRANGE: Fixture provides code with specific docstrings

    # 2. ACT: Generate skeleton
    result = generate_skeleton_code(calculator_source)

    # 3. ASSERT: Architectural context (docstrings) must persist
    assert '"""Clase simple para operaciones aritméticas."""' in result
    assert '"""Suma un número al valor actual."""' in result
    assert '"""Función fuera de clase."""' in result


@pytest.mark.unit
def test_generate_skeleton_preserves_decorators_and_async():
    """
    Verifies that async definitions and decorators remain intact.
    Uses an ad-hoc string to test specific syntax.
    """
    # 1. ARRANGE: Source with decorators and async keywords
    source = (
        "@app.route('/')\n"
        "async def index():\n"
        "    return await render_template('index.html')"
    )

    # 2. ACT: Transform
    result = generate_skeleton_code(source)

    # 3. ASSERT: Execution context must remain visible
    assert "@app.route('/')" in result
    assert "async def index():" in result
    assert "pass" in result


@pytest.mark.unit
def test_generate_skeleton_handles_classes_recursively(calculator_source):
    """
    Ensures classes and all their internal methods are skeletonized.
    Fixes fragility caused by ast.unparse() whitespace normalization.
    """
    # 1. ARRANGE: Code with default arguments 'int = 0'

    # 2. ACT: Execute skeletonization
    result = generate_skeleton_code(calculator_source)

    # 3. ASSERT: Verify structural integrity ignoring minor whitespace changes
    assert "class Calculator:" in result
    # We strip spaces in default args to match ast.unparse() behavior: 'int=0'
    normalized_result = result.replace(" ", "")
    assert "def__init__(self,initial_value:int=0):" in normalized_result
    assert "def_internal_reset(self):" in normalized_result

    # Ensures all methods were replaced by 'pass'
    assert result.count("pass") >= 4


@pytest.mark.unit
def test_generate_skeleton_removes_top_level_logic(calculator_source):
    """
    To optimize token density, non-definition code (imports/globals)
    must be pruned in skeleton mode.
    """
    # 1. ARRANGE
    # 2. ACT
    result = generate_skeleton_code(calculator_source)

    # 3. ASSERT: Only definitions (Class/Func) and their internal docstrings survive
    assert "Logic executed" not in result
    # The transformer prunes top-level module logic and assignments
    assert "Módulo principal de calculadora." not in result


@pytest.mark.unit
def test_generate_skeleton_handles_syntax_error_gracefully():
    """
    If the input code is invalid, return a diagnostic message instead of crashing.
    """
    # 1. ARRANGE: Intentional SyntaxError (missing closing parenthesis)
    source = "def broken_code(a, b:"

    # 2. ACT
    result = generate_skeleton_code(source)

    # 3. ASSERT: Safe failure reporting
    assert "[SKIPPING SKELETON]" in result
    assert "SyntaxError" in result


@pytest.mark.unit
def test_generate_skeleton_handles_empty_input():
    """
    Edge case: Empty strings should not trigger AST errors.
    """
    # 2. ACT & 3. ASSERT
    assert generate_skeleton_code("") == ""
    assert generate_skeleton_code("   \n   ") == ""