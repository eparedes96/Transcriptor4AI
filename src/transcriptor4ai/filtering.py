from __future__ import annotations

"""
File and directory filtering logic.

Provides regex-based inclusion and exclusion patterns for the scanner.
"""

import fnmatch
import os
import re
from typing import List

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# Extensions typically associated with configuration, documentation, or data.
_RESOURCE_EXTENSIONS = {
    ".md", ".markdown", ".rst", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".ini", ".cfg", ".conf", ".properties",
    ".dockerignore", ".editorconfig"
}

# Exact filenames considered resources
_RESOURCE_FILENAMES = {
    "Dockerfile", "Makefile", "LICENSE", "CHANGELOG", "README", "Gemfile", "Procfile"
}


# -----------------------------------------------------------------------------
# Default Filters & Helpers
# -----------------------------------------------------------------------------
def default_extensions() -> List[str]:
    return [".py"]


def default_include_patterns() -> List[str]:
    return [".*"]


def default_exclude_patterns() -> List[str]:
    """
    Default exclusion patterns (applied via re.match).

    Excludes:
      - __init__.py
      - Compiled files (*.pyc)
      - Directories: __pycache__, .git, .idea
      - Hidden files (starting with .)
    """
    return [
        r"^__init__\.py$",
        r".*\.pyc$",
        r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
        r"^\.",
    ]


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """Compile a list of regex strings into Pattern objects."""
    compiled: List[re.Pattern] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


def matches_any(name: str, compiled_patterns: List[re.Pattern]) -> bool:
    """Return True if 'name' matches ANY of the provided patterns."""
    return any(rx.search(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    """Return True if 'name' matches inclusion patterns (or if list is empty/permissive)."""
    if not include_patterns:
        return False
    return any(rx.search(name) for rx in include_patterns)


# -----------------------------------------------------------------------------
# File Classification
# -----------------------------------------------------------------------------
def is_test(file_name: str) -> bool:
    """
    Detect if a file is a test file based on naming convention.

    Matches patterns:
    - Standard: test_*.py, *_test.py
    - Java/C#: *Test.java, *Tests.cs, *TestCase.java
    - Web/Modern: *.spec.ts, *.test.js, *.e2e.js, *.cy.ts
    - Go: *_test.go
    """
    pattern = (
        r"^(test_.*|.*_test|.*Test|.*Tests|.*TestCase|.*\.spec|.*\.test|.*\.e2e|.*\.cy)"
        r"\.(py|js|ts|jsx|tsx|java|kt|go|rs|cs|cpp|c|h|hpp|swift|php)$"
    )
    return re.match(pattern, file_name, re.IGNORECASE) is not None


def is_resource_file(file_name: str) -> bool:
    """
    Detect if a file is a resource (config, doc, data) based on extension or exact name.
    """
    if file_name in _RESOURCE_FILENAMES:
        return True

    _, ext = os.path.splitext(file_name)
    return ext.lower() in _RESOURCE_EXTENSIONS


# -----------------------------------------------------------------------------
# Gitignore Support
# -----------------------------------------------------------------------------
def load_gitignore_patterns(root_path: str) -> List[str]:
    """
    Parse .gitignore at the root_path and return a list of regex strings.

    Limitation: Supports basic glob patterns. Does not fully support
    advanced negation (!) or nested .gitignore files yet.
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
    """Convert a gitignore glob pattern to a Python regex string."""
    if glob_pattern.endswith("/"):
        glob_pattern = glob_pattern.rstrip("/")

    try:
        regex = fnmatch.translate(glob_pattern)

        if "/" not in glob_pattern:
            return regex
        else:
            return regex
    except Exception:
        return ""