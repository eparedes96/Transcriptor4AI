from __future__ import annotations

"""
AST Parser Edge Cases Unit Tests.

Validates the structural resilience of the static analysis engine against
complex, modern, and unconventional Python syntax (lambdas, deep decorators,
positional-only arguments, and empty entities).
"""

import textwrap
from pathlib import Path

import pytest

from transcriptor4ai.application.analysis.ast_parser import (
    extract_definitions,
    generate_skeleton_code,
)

# ==============================================================================
# TEST GROUP: AST PARSER EDGE CASES & COMPLEX SYNTAX
# ==============================================================================

@pytest.mark.unit
def test_ast_should_preserve_nested_and_factory_decorators() -> None:
    """
    Verifies that multiple stacked decorators, including those with
    arguments (factories), are fully preserved in the generated skeleton.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    # Complex decorator structure
    source_code = textwrap.dedent("""
        @app.route('/api/v1/users', methods=['GET', 'POST'])
        @require_auth(level='admin')
        @cache_response(ttl=3600)
        def get_users(request):
            \"\"\"Fetch all users.\"\"\"
            db_conn = get_db()
            users = db_conn.query("SELECT * FROM users")
            return [u.to_dict() for u in users]
    """).strip()

    # 2. ACT: Execute the specific behavior/method
    skeleton = generate_skeleton_code(source_code)

    # 3. ASSERT: Verify the outcome and side effects
    # Ensures decorators remain untouched while the logic is stripped
    assert "@app.route('/api/v1/users', methods=['GET', 'POST'])" in skeleton
    assert "@require_auth(level='admin')" in skeleton
    assert "@cache_response(ttl=3600)" in skeleton
    assert '"""Fetch all users."""' in skeleton
    assert "db_conn =" not in skeleton
    assert "pass" in skeleton


@pytest.mark.unit
def test_ast_should_ignore_lambdas_and_strip_them_from_module() -> None:
    """
    Ensures that lambda assignments do not crash the parser.
    Lambdas are expressions, not FunctionDefs, so they should be excluded
    from the module-level definitions.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    source_code = textwrap.dedent("""
        import sys

        # Global lambda assignment
        fast_math = lambda x, y: x**y + 100

        def standard_function():
            return fast_math(2, 3)
    """).strip()

    # 2. ACT: Execute the specific behavior/method
    skeleton = generate_skeleton_code(source_code)

    # 3. ASSERT: Verify the outcome and side effects
    # Module visitor strips everything that is not ClassDef or FunctionDef
    assert "fast_math =" not in skeleton
    assert "lambda x, y" not in skeleton
    assert "def standard_function():" in skeleton
    assert "pass" in skeleton


@pytest.mark.unit
def test_ast_should_handle_modern_type_hints_and_positional_only_args() -> None:
    """
    Validates compatibility with modern Python features:
    positional-only arguments (/), keyword-only arguments (*),
    and complex type hinting generics.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    source_code = textwrap.dedent("""
        from typing import Union, Callable

        def complex_signature(
            uid: int,
            /,
            payload: dict[str, list[Union[int, float]]],
            *,
            callback: Callable[[str], None] = None
        ) -> bool:
            # Complex body
            try:
                callback(str(uid))
                return True
            except Exception:
                return False
    """).strip()

    # 2. ACT: Execute the specific behavior/method
    skeleton = generate_skeleton_code(source_code)

    # 3. ASSERT: Verify the outcome and side effects
    # We remove whitespace for assertion to avoid AST unparse formatting differences
    normalized_skeleton = skeleton.replace(" ", "").replace("\n", "")

    # Ensures signatures survive the AST reconstruction perfectly
    assert "defcomplex_signature(uid:int,/,payload:dict[str,list[Union[int,float]]],*,callback:Callable[[str],None]=None)->bool:pass" in normalized_skeleton
    assert "callback(str(uid))" not in skeleton


@pytest.mark.unit
def test_ast_should_process_empty_classes_without_methods(tmp_path: Path) -> None:
    """
    Ensures that classes lacking internal methods (e.g., Marker classes,
    Exceptions, Dataclasses without methods) are processed correctly by both
    the Skeleton engine and the Definition Extractor.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    source_code = textwrap.dedent("""
        class CustomError(Exception):
            \"\"\"Raised when something goes terribly wrong.\"\"\"
            pass

        class EmptyMarker:
            pass
    """).strip()

    test_file = tmp_path / "empty_classes.py"
    test_file.write_text(source_code, encoding="utf-8")

    # 2. ACT: Execute the specific behavior/method
    skeleton = generate_skeleton_code(source_code)
    definitions = extract_definitions(
        file_path=test_file,
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    # A. Skeleton assertions
    assert "class CustomError(Exception):" in skeleton
    assert '"""Raised when something goes terribly wrong."""' in skeleton
    assert "class EmptyMarker:" in skeleton

    # B. Extraction assertions
    assert "Class: CustomError" in definitions
    assert "Class: EmptyMarker" in definitions
    assert len(definitions) == 2  # No phantom methods should be extracted


@pytest.mark.unit
def test_ast_should_destroy_inner_functions_in_skeleton_mode() -> None:
    """
    Business Rule: Inner functions (defined inside another function)
    are implementation details. The Skeletonization process must completely
    erase them since the parent function's body is replaced by `pass`.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    source_code = textwrap.dedent("""
        def outer_controller():
            \"\"\"Main entry point.\"\"\"

            def _secret_inner_logic(x):
                return x * 99

            class InnerClassNotExposed:
                pass

            return _secret_inner_logic(10)
    """).strip()

    # 2. ACT: Execute the specific behavior/method
    skeleton = generate_skeleton_code(source_code)

    # 3. ASSERT: Verify the outcome and side effects
    assert "def outer_controller():" in skeleton
    assert '"""Main entry point."""' in skeleton

    # The internals must be entirely purged
    assert "def _secret_inner_logic" not in skeleton
    assert "class InnerClassNotExposed" not in skeleton
    assert "return _secret_inner_logic" not in skeleton


@pytest.mark.unit
def test_ast_extract_definitions_ignores_lambdas_but_catches_async(tmp_path: Path) -> None:
    """
    Validates that the extraction logic correctly identifies Async functions
    but strictly ignores lambda assignments to variables.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    source_code = textwrap.dedent("""
        async def fetch_remote_data():
            await asyncio.sleep(1)

        inline_process = lambda a: a + 1
    """).strip()

    test_file = tmp_path / "async_lambda.py"
    test_file.write_text(source_code, encoding="utf-8")

    # 2. ACT: Execute the specific behavior/method
    definitions = extract_definitions(
        file_path=test_file,
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    assert "Function: fetch_remote_data()" in definitions
    assert not any("inline_process" in d for d in definitions)
    assert not any("lambda" in d for d in definitions)
    assert len(definitions) == 1