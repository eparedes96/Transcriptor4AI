from __future__ import annotations

"""
Global Pytest Configuration and Fixtures.

This module sets up the testing environment, including:
1. Path manipulation to ensure the 'src' directory is importable.
2. Shared fixtures for configuration dictionaries used across unit tests.
"""

import os
import sys
from typing import Any, Dict

import pytest

# -----------------------------------------------------------------------------
# Path Configuration
# -----------------------------------------------------------------------------
_SRC_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)


# -----------------------------------------------------------------------------
# Shared Fixtures
# -----------------------------------------------------------------------------
@pytest.fixture
def mock_config_dict() -> Dict[str, Any]:
    """
    Return a valid, complete configuration dictionary for testing.

    Reflects the structure defined in 'transcriptor4ai.domain.config',
    ensuring all keys expected by the pipeline are present.

    Returns:
        Dict[str, Any]: A sample configuration dictionary.
    """
    return {
        # IO Paths
        "input_path": "/tmp/test_input",
        "output_base_dir": "/tmp/test_output",
        "output_subdir_name": "transcript",
        "output_prefix": "test_output",

        # Content Selection
        "process_modules": True,
        "process_tests": True,
        "process_resources": False,

        # Output Format
        "create_individual_files": True,
        "create_unified_file": True,

        # Filtering
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [],
        "respect_gitignore": True,
        "target_model": "GPT-4o / GPT-5",

        # Tree & AST
        "generate_tree": False,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": False,

        # Optimization & Security
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # Diagnostics
        "save_error_log": True
    }