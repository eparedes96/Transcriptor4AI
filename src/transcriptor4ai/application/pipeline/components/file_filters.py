from __future__ import annotations

"""
File Filtering and Classification Engine.

Implements regex-based inclusion/exclusion logic and provides heuristic 
classification to distinguish between source modules, test suites, and 
project resources. Supports integration with .gitignore glob patterns.
"""

import fnmatch
import os
import re
from typing import List, Set

# -----------------------------------------------------------------------------
# REGEX AND FILENAME CONSTANTS
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
# CONFIGURATION DEFAULTS
# -----------------------------------------------------------------------------

def default_extensions() -> List[str]:
    """
    Get the default list of targeted file extensions.

    Returns:
        List[str]: List containing standard source file extensions.
    """
    return [".py"]


def default_include_patterns() -> List[str]:
    """
    Get the default inclusion regex list.

    Returns:
        List[str]: List of regex strings that match everything by default.
    """
    return [".*"]


def default_exclude_patterns() -> List[str]:
    """
    Get the system-level exclusion patterns.

    Identifies common development noise, compiled artifacts, and
    environment-specific directories that should be skipped by default.

    Returns:
        List[str]: List of regex patterns for common exclusions.
    """
    return [
        r"^__init__\.py$",
        r".*\.pyc$",
        r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
        r"^\.",
    ]

# -----------------------------------------------------------------------------
# PATTERN COMPILATION AND MATCHING
# -----------------------------------------------------------------------------

def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """
    Transform raw regex strings into compiled Pattern objects.

    Provides a fail-safe mechanism that discards malformed regex strings
    to prevent pipeline crashes during execution.

    Args:
        patterns: List of raw regex strings.

    Returns:
        List[re.Pattern]: Compiled regex objects.
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
    Verify if a string matches at least one compiled regex pattern.

    Args:
        name: Filename or directory name to evaluate.
        compiled_patterns: Pre-compiled regex objects.

    Returns:
        bool: True if any match is found, False otherwise.
    """
    return any(rx.search(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    """
    Verify if a string satisfies the inclusion whitelist.

    Args:
        name: Filename to evaluate.
        include_patterns: Compiled inclusion regex objects.

    Returns:
        bool: True if matched, False if the list is empty or no match occurs.
    """
    if not include_patterns:
        return False
    return any(rx.search(name) for rx in include_patterns)

# -----------------------------------------------------------------------------
# FILE CLASSIFICATION LOGIC
# -----------------------------------------------------------------------------

def is_test(file_name: str) -> bool:
    """
    Classify a file as a test suite based on polyglot naming conventions.

    Supports Python (test_*), Java/C# (Test*), JS/TS (*.spec), and Go
    patterns across common development languages.

    Args:
        file_name: Target filename.

    Returns:
        bool: True if the filename matches common test patterns.
    """
    pattern = (
        r"^(test_.*|.*_test|Test.*|.*Test|.*Tests|.*TestCase|.*\.spec|.*\.test|.*\.e2e|.*\.cy)"
        r"\.(py|js|ts|jsx|tsx|java|kt|go|rs|cs|cpp|c|h|hpp|swift|php)$"
    )
    return re.match(pattern, file_name, re.IGNORECASE) is not None


def is_resource_file(file_name: str) -> bool:
    """
    Classify a file as a non-code project resource.

    Evaluates both explicit filenames (like Dockerfile) and specific
    extensions commonly used for documentation and configuration.

    Args:
        file_name: Target filename.

    Returns:
        bool: True if the file is identified as a resource.
    """
    # High-priority check for explicit filenames
    if file_name in _RESOURCE_FILENAMES:
        return True

    # Extension-based classification
    _, ext = os.path.splitext(file_name)
    return ext.lower() in _RESOURCE_EXTENSIONS

# -----------------------------------------------------------------------------
# GITIGNORE INTEGRATION
# -----------------------------------------------------------------------------

def load_gitignore_patterns(root_path: str) -> List[str]:
    """
    Parse a .gitignore file and translate its glob rules into Python regexes.

    Args:
        root_path: Parent directory containing the .gitignore file.

    Returns:
        List[str]: List of equivalent regex strings.
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
    Helper to translate gitignore/shell glob syntax to Python regex.

    Args:
        glob_pattern: Raw glob pattern from .gitignore.

    Returns:
        str: Valid Python regex string.
    """
    if glob_pattern.endswith("/"):
        glob_pattern = glob_pattern.rstrip("/")

    try:
        return fnmatch.translate(glob_pattern)
    except Exception:
        return ""