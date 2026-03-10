from __future__ import annotations

"""
File Filtering and Classification Engine.

Implements regex-based inclusion/exclusion logic and provides heuristic 
classification to distinguish between source modules, test suites, and 
project resources. Centralizes the domain policies for file categorization 
to ensure consistency across scanning and transcription phases.
"""

import fnmatch
import logging
import os
import re
from typing import Final, List, Set

# ==============================================================================
# GLOBAL LOGGER CONFIGURATION
# ==============================================================================
logger = logging.getLogger(__name__)

# ==============================================================================
# CLASSIFICATION CONSTANTS
# ==============================================================================

_RESOURCE_EXTENSIONS: Final[Set[str]] = {
    ".md", ".markdown", ".rst", ".txt",
    ".json", ".yaml", ".yml", ".toml", ".xml", ".csv", ".ini", ".cfg", ".conf", ".properties",
    ".dockerignore", ".editorconfig", ".css", ".env"
}

_RESOURCE_FILENAMES: Final[Set[str]] = {
    "Dockerfile", "Makefile", "LICENSE", "CHANGELOG", "README", "Gemfile", "Procfile",
    ".dockerignore", ".editorconfig", ".env", ".gitignore"
}


# ==============================================================================
# PIPELINE CONFIGURATION DEFAULTS
# ==============================================================================

def default_extensions() -> List[str]:
    """Get the default list of targeted file extensions."""
    return [".py"]


def default_include_patterns() -> List[str]:
    """Get the default inclusion regex list (match all)."""
    return [".*"]


def default_exclude_patterns() -> List[str]:
    """Get the system-level exclusion patterns for noise reduction."""
    return [
        r"^__init__\.py$",
        r".*\.pyc$",
        r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
        r"^\.",
    ]


# ==============================================================================
# PATTERN COMPILATION AND MATCHING
# ==============================================================================

def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    """
    Transform raw regex strings into compiled Pattern objects.
    Discards malformed regex strings to prevent execution crashes.
    """
    compiled: List[re.Pattern] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


def matches_any(name: str, compiled_patterns: List[re.Pattern]) -> bool:
    """Verify if a string matches at least one compiled regex pattern."""
    return any(rx.search(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    """Verify if a string satisfies the inclusion whitelist."""
    if not include_patterns:
        return False
    return any(rx.search(name) for rx in include_patterns)


# ==============================================================================
# DOMAIN POLICY: FILE CLASSIFICATION
# ==============================================================================

def determine_target_mode(
        file_name: str,
        depth: str,
        process_tests: bool,
        process_resources: bool
) -> str:
    """
    Apply domain policies to categorize a file for the transcription pipeline.

    Args:
        file_name: Base name of the file to classify.
        depth: Current processing depth ('full', 'skeleton', 'tree_only').
        process_tests: Whether tests are enabled in config.
        process_resources: Whether non-code resources are enabled.

    Returns:
        str: Target category ('module', 'test', 'resource', 'skip').
    """
    # 1. DEPTH CHECK: Early exit if processing logic is disabled
    if depth == "tree_only":
        return "skip"

    # 2. TYPE EVALUATION
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)

    # 3. ROUTING LOGIC
    if file_is_test:
        return "test" if process_tests else "skip"

    if file_is_resource:
        return "resource" if process_resources else "module"

    return "module"


def is_test(file_name: str) -> bool:
    """
    Classify a file as a test suite based on polyglot naming conventions.

    Uses a strict pattern to avoid false positives like 'attest.py' or 'testing_utils.py'
    by requiring logical boundaries (underscores, dots, or PascalCase).
    """
    # 1. test_... or ..._test (Python/Ruby snake_case)
    # 2. Test[A-Z]... or ...Test (Java/C# PascalCase)
    # 3. test[A-Z]... (JS/TS camelCase)
    # 4. .spec, .test, .e2e, .cy (Web/Modern JS)
    test_pattern = (
        r"^(test_.*|.*_test|Test[A-Z].*|test[A-Z].*|[A-Z].*Test|"
        r".*\.spec|.*\.test|.*\.e2e|.*\.cy)"
    )

    # Extension suffix (polyglot support)
    extension_pattern = (
        r"\.(py|js|ts|jsx|tsx|java|kt|go|rs|cs|cpp|c|h|hpp|swift|php)$"
    )

    full_regex = f"{test_pattern}{extension_pattern}"

    # Re-compiled without global IGNORECASE to maintain PascalCase/snake_case semantic precision
    return re.match(full_regex, file_name) is not None


def is_resource_file(file_name: str) -> bool:
    """Classify a file as a non-code project resource (Docs/Config/Data)."""
    if file_name in _RESOURCE_FILENAMES:
        return True

    _, ext = os.path.splitext(file_name)
    return ext.lower() in _RESOURCE_EXTENSIONS


# ==============================================================================
# INFRASTRUCTURE INTEGRATION: GITIGNORE
# ==============================================================================

def load_gitignore_patterns(root_path: str) -> List[str]:
    """
    Parse .gitignore and translate glob rules into Python regexes.

    Handles missing files and I/O errors gracefully.
    """
    gitignore_path = os.path.join(root_path, ".gitignore")
    if not os.path.exists(gitignore_path):
        return []

    regex_patterns: List[str] = []
    try:
        with open(gitignore_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith("#"):
                    continue

                regex = _gitignore_to_regex(line)
                if regex:
                    regex_patterns.append(regex)
    except (OSError, UnicodeDecodeError) as e:
        # Uses module-level logger to record the failure
        logger.debug(f"Filters: Gitignore parse error in {root_path}: {e}")

    return regex_patterns


def _gitignore_to_regex(glob_pattern: str) -> str:
    """Helper to translate gitignore/shell glob syntax to Python regex."""
    if glob_pattern.endswith("/"):
        glob_pattern = glob_pattern.rstrip("/")

    try:
        return fnmatch.translate(glob_pattern)
    except (re.error, TypeError):
        return ""