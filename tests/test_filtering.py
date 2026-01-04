# tests/test_filtering.py
import re
import pytest
from transcriptor4ai.filtering import (
    compile_patterns,
    matches_any,
    es_test,
    default_exclude_patterns
)


# -----------------------------------------------------------------------------
# 1. Regex Compilation Logic
# -----------------------------------------------------------------------------
def test_compile_patterns_handles_valid_and_invalid():
    """Verify that valid patterns compile and invalid ones are skipped."""
    patterns = [r"^valid.*", r"[invalid_regex"]
    compiled = compile_patterns(patterns)

    assert len(compiled) == 1
    assert isinstance(compiled[0], re.Pattern)


# -----------------------------------------------------------------------------
# 2. Matching Logic (Exclusions/Inclusions)
# -----------------------------------------------------------------------------
def test_default_exclusions():
    """Ensure default patterns block common noise files."""
    defaults = default_exclude_patterns()
    compiled = compile_patterns(defaults)

    # Should match (Exclude)
    assert matches_any("__init__.py", compiled) is True
    assert matches_any("script.pyc", compiled) is True
    assert matches_any(".git", compiled) is True
    assert matches_any(".env", compiled) is True
    assert matches_any("__pycache__", compiled) is True

    # Should NOT match (Include)
    assert matches_any("main.py", compiled) is False
    assert matches_any("data.json", compiled) is False


def test_custom_inclusion_logic():
    """Test custom inclusion patterns."""
    patterns = [r".*\.py$", r".*\.md$"]
    compiled = compile_patterns(patterns)

    assert matches_any("script.py", compiled) is True
    assert matches_any("readme.md", compiled) is True
    assert matches_any("image.png", compiled) is False


# -----------------------------------------------------------------------------
# 3. Test File Detection
# -----------------------------------------------------------------------------
def test_es_test_identification():
    """Verify classification of Test vs Source files."""
    # Positives
    assert es_test("test_api.py") is True
    assert es_test("api_test.py") is True
    assert es_test("test_utils.py") is True

    # Negatives
    assert es_test("api.py") is False
    assert es_test("test_helper.txt") is False  # Extension check is usually done before, but regex expects .py
    assert es_test("latest_results.py") is False