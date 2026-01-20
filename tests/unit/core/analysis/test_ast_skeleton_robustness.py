from __future__ import annotations

"""
Robustness tests for the AST Skeletonizer.

Stresses the ast_parser with edge cases: syntax errors, empty files,
complex decorators, and async structures to ensure fail-safe behavior.
"""

from transcriptor4ai.core.analysis.ast_parser import generate_skeleton_code


def test_skeletonizer_syntax_error_fallback() -> None:
    """TC-01: Ensure skeletonizer handles invalid Python code gracefully."""
    invalid_code = "def incomplete_func(:"
    result = generate_skeleton_code(invalid_code)
    assert "[SKIPPING SKELETON]" in result
    assert "syntax errors" in result


def test_skeletonizer_complex_structures() -> None:
    """TC-02: Verify preservation of decorators, async, and docstrings."""
    source = (
        "@decorator\n"
        "async def complex_task(a: int) -> bool:\n"
        "    '''Do something.'''\n"
        "    x = 1\n"
        "    return True"
    )
    result = generate_skeleton_code(source)

    assert "@decorator" in result
    assert "async def complex_task" in result
    assert '"""Do something."""' in result
    assert "x = 1" not in result
    assert "return True" not in result
    assert "pass" in result


def test_skeletonizer_empty_and_no_body() -> None:
    """TC-03: Verify handling of empty files or files without functions."""
    source = "VAR = 123\n# Just a comment"
    result = generate_skeleton_code(source)
    assert "VAR = 123" not in result