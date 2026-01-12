from __future__ import annotations

"""
File filtering logic.

Provides regex-based inclusion/exclusion matching and utility functions
to classify files (tests vs code, resources vs logic).
"""

import fnmatch
import os
import re
from typing import List, Set

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_RESOURCE_EXTENSIONS: Set[str] = {
    ".md", ".markdown", ".rst", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".ini", ".cfg", ".conf", ".properties",
    ".dockerignore", ".editorconfig", ".css", ".env"
}

_RESOURCE_FILENAMES: Set[str] = {
    "Dockerfile", "Makefile", "LICENSE", "CHANGELOG", "README", "Gemfile", "Procfile",
    ".dockerignore", ".editorconfig", ".env", ".gitignore"
}


# -----------------------------------------------------------------------------
# Defaults
# -----------------------------------------------------------------------------
def default_extensions() -> List[str]:
    """Return default allowed extensions."""
    return [".py"]


def default_include_patterns() -> List[str]:
    """Return default inclusion regex patterns (match all)."""
    return [".*"]


def default_exclude_patterns() -> List[str]:
    """
    Return default exclusion patterns.

    Excludes:
      - __init__.py
      - Compiled files (*.pyc)
      - Directories: __pycache__, .git, .idea, .vscode, node_modules
      - Hidden files (starting with .)
    """
    return [
        r"^__init__\.py$",
        r".*\.pyc$",
        r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
        r"^\.",
    ]


# -----------------------------------------------------------------------------
# Compilation & Matching
# -----------------------------------------------------------------------------
def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """
    Compile a list of regex strings into Pattern objects.
    Silently ignores invalid regex patterns.

    Args:
        patterns: List of regex strings.

    Returns:
        List[re.Pattern]: List of compiled pattern objects.
    """
    compiled: List[re.Pattern] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


def matches_any(name: str, compiled_patterns: List[re.Pattern]) -> bool:
    """
    Check if a name matches ANY of the provided patterns.

    Args:
        name: The filename or directory name to check.
        compiled_patterns: List of compiled regex patterns.

    Returns:
        bool: True if at least one match is found.
    """
    return any(rx.search(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    """
    Check if a name matches inclusion patterns.
    If no inclusion patterns are provided, returns False (nothing included).

    Args:
        name: The filename to check.
        include_patterns: List of inclusion patterns.

    Returns:
        bool: True if matched.
    """
    if not include_patterns:
        return False
    return any(rx.search(name) for rx in include_patterns)


# -----------------------------------------------------------------------------
# Classification
# -----------------------------------------------------------------------------
def is_test(file_name: str) -> bool:
    """
    Detect if a file is a test file based on naming convention.

    Matches:
    - Python: test_*.py, *_test.py
    - Java/C#: Test*.java, *Test.java, *Tests.cs
    - JS/TS: *.spec.ts, *.test.js, *.cy.ts
    - Go: *_test.go

    Args:
        file_name: The name of the file.

    Returns:
        bool: True if it looks like a test.
    """
    pattern = (
        r"^(test_.*|.*_test|Test.*|.*Test|.*Tests|.*TestCase|.*\.spec|.*\.test|.*\.e2e|.*\.cy)"
        r"\.(py|js|ts|jsx|tsx|java|kt|go|rs|cs|cpp|c|h|hpp|swift|php)$"
    )
    return re.match(pattern, file_name, re.IGNORECASE) is not None


def is_resource_file(file_name: str) -> bool:
    """
    Detect if a file is a resource (config, doc, data) based on extension or explicit name.

    Args:
        file_name: The name of the file.

    Returns:
        bool: True if it is a resource.
    """
    # Check exact filenames first (e.g. Dockerfile)
    if file_name in _RESOURCE_FILENAMES:
        return True

    # Check extension
    _, ext = os.path.splitext(file_name)
    return ext.lower() in _RESOURCE_EXTENSIONS


# -----------------------------------------------------------------------------
# Gitignore Integration
# -----------------------------------------------------------------------------
def load_gitignore_patterns(root_path: str) -> List[str]:
    """
    Parse .gitignore at the root_path and return a list of regex strings.

    Args:
        root_path: The directory containing .gitignore.

    Returns:
        List[str]: List of regex strings equivalent to the gitignore rules.
    """
    gitignore_path = os.path.join(root_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        return []

    regex_patterns: List[str] = []
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                regex = _gitignore_to_regex(line)
                if regex:
                    regex_patterns.append(regex)
    except Exception:
        pass

    return regex_patterns


def _gitignore_to_regex(glob_pattern: str) -> str:
    """
    Convert a gitignore glob pattern to a Python regex string.

    Args:
        glob_pattern: The glob string (e.g., "*.log").

    Returns:
        str: The translated regex string.
    """
    if glob_pattern.endswith("/"):
        glob_pattern = glob_pattern.rstrip("/")

    try:
        return fnmatch.translate(glob_pattern)
    except Exception:
        return ""