from __future__ import annotations

"""
Unit tests for filtering logic (Regex, Defaults, Test detection, Resources, Gitignore).
"""

import os
import re
import pytest
from transcriptor4ai.filtering import (
    compile_patterns,
    matches_any,
    is_test,
    default_exclude_patterns,
    is_resource_file,
    _gitignore_to_regex,
    load_gitignore_patterns
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
def test_is_test_identification():
    """Verify classification of Test vs Source files."""
    # Positives
    assert is_test("test_api.py") is True
    assert is_test("api_test.py") is True
    assert is_test("test_utils.py") is True

    # Negatives
    assert is_test("api.py") is False
    assert is_test("test_helper.txt") is False
    assert is_test("latest_results.py") is False


# -----------------------------------------------------------------------------
# 4. Resource File Detection
# -----------------------------------------------------------------------------
def test_is_resource_file():
    """Verify classification of Resource files (Docs/Config) vs Code."""
    # True cases (Extensions & Filenames)
    assert is_resource_file("README.md") is True
    assert is_resource_file("config.json") is True
    assert is_resource_file("Dockerfile") is True
    assert is_resource_file("data.csv") is True

    # False cases (Source Code)
    assert is_resource_file("main.py") is False
    assert is_resource_file("script.js") is False
    assert is_resource_file("test_utils.py") is False


# -----------------------------------------------------------------------------
# 5. Gitignore Logic
# -----------------------------------------------------------------------------
def test_gitignore_to_regex_conversion():
    """Verify glob to regex conversion."""
    # Case 1: Extension wildcards
    rx = _gitignore_to_regex("*.log")
    assert rx.startswith("(?s:")
    assert "log" in rx

    # Case 2: Specific Directory
    rx_dir = _gitignore_to_regex("node_modules/")
    assert "node_modules" in rx_dir


def test_load_gitignore_integration(tmp_path):
    """Create a dummy .gitignore and verify it blocks files."""
    root = tmp_path
    gitignore = root / ".gitignore"
    gitignore.write_text("*.secret\nbuild", encoding="utf-8")

    patterns = load_gitignore_patterns(str(root))
    compiled = compile_patterns(patterns)

    # Should be blocked
    assert matches_any("api_key.secret", compiled) is True
    assert matches_any("folder/other.secret", compiled) is True
    assert matches_any("build", compiled) is True

    # Should NOT be blocked
    assert matches_any("main.py", compiled) is False