from __future__ import annotations

"""
File and directory filtering logic.

Provides regex-based inclusion and exclusion patterns for the scanner.
"""

import re
from typing import List

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
        r"^(__pycache__|\.git|\.idea)$",
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
    return any(rx.match(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    """Return True if 'name' matches inclusion patterns (or if list is empty/permissive)."""
    if not include_patterns:
        return False
    return any(rx.match(name) for rx in include_patterns)


def is_test(file_name: str) -> bool:
    """
    Detect if a file is a test file based on naming convention.
    Matches: test_*.py or *_test.py
    """
    return re.match(r"^(test_.*\.py|.*_test\.py)$", file_name) is not None