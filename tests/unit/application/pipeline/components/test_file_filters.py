from __future__ import annotations

"""
Unit tests for the File Filters module.

Verifies:
1. Regex compilation and matching logic.
2. File classification (Test vs Resource vs Code).
3. Integration with .gitignore parsing.
"""

import re

from transcriptor4ai.core.pipeline.components.filters import (
    _gitignore_to_regex,
    compile_patterns,
    default_exclude_patterns,
    is_resource_file,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)


def test_compile_patterns_handles_valid_and_invalid():
    """Verify that valid patterns compile and invalid ones are skipped silently."""
    patterns = [r"^valid.*", r"[invalid_regex", r"normal"]
    compiled = compile_patterns(patterns)

    assert len(compiled) == 2
    assert isinstance(compiled[0], re.Pattern)


def test_matches_any_logic():
    """Test the 'OR' logic of exclusion patterns."""
    patterns = [r"^ignore_me", r".*\.tmp$"]
    compiled = compile_patterns(patterns)

    assert matches_any("ignore_me_folder", compiled) is True
    assert matches_any("file.tmp", compiled) is True
    assert matches_any("keep_me.txt", compiled) is False


def test_matches_include_logic():
    """Test inclusion patterns. Empty list should match nothing."""
    # Case 1: Specific include
    compiled = compile_patterns([r"\.py$"])
    assert matches_include("script.py", compiled) is True
    assert matches_include("readme.md", compiled) is False

    # Case 2: Empty list (Defensive check)
    assert matches_include("script.py", []) is False


def test_default_exclusions_block_common_noise():
    """Ensure default patterns effectively block git, cache, and env files."""
    defaults = compile_patterns(default_exclude_patterns())

    noise_files = [
        ".git",
        ".env",
        "__pycache__",
        "script.pyc",
        "node_modules",
        ".vscode",
        ".idea"
    ]

    for f in noise_files:
        assert matches_any(f, defaults) is True, f"Failed to exclude {f}"

    assert matches_any("main.py", defaults) is False


def test_is_test_identification_polyglot():
    """
    Verify classification of Test files across multiple languages.
    """
    test_files = [
        "test_api.py", "api_test.py", "TestUser.java",
        "user.spec.ts", "component.test.js", "auth_test.go",
        "UserServiceTests.cs"
    ]

    normal_files = [
        "api.py", "test_helper.txt", "latest_results.json",
        "User.java", "spec.md"
    ]

    for f in test_files:
        assert is_test(f) is True, f"{f} should be a test"

    for f in normal_files:
        assert is_test(f) is False, f"{f} should NOT be a test"


def test_is_resource_file_identification():
    """Verify detection of config, data, and documentation files."""
    resources = [
        "README.md", "Dockerfile", "config.json", "data.csv",
        "styles.css", ".dockerignore", "ci.yml"
    ]

    code = ["main.py", "script.sh", "app.js"]

    for f in resources:
        assert is_resource_file(f) is True, f"{f} should be a resource"

    for f in code:
        assert is_resource_file(f) is False, f"{f} should be code"


def test_gitignore_to_regex_conversion():
    """Verify glob to regex translation for gitignore rules."""
    # Basic glob
    assert "log" in _gitignore_to_regex("*.log")
    # Directory
    assert "node_modules" in _gitignore_to_regex("node_modules/")


def test_load_gitignore_integration(tmp_path):
    """Create a dummy .gitignore and verify it generates valid regex strings."""
    root = tmp_path
    gitignore = root / ".gitignore"
    gitignore.write_text("*.secret\nbuild/\n# Comment", encoding="utf-8")

    patterns = load_gitignore_patterns(str(root))

    # Should contain regex for *.secret and build/
    assert len(patterns) >= 2

    compiled = compile_patterns(patterns)
    assert matches_any("api.secret", compiled) is True
    assert matches_any("build", compiled) is True
    assert matches_any("main.py", compiled) is False