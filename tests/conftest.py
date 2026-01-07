from __future__ import annotations

"""
Test configuration and shared fixtures for transcriptor4ai.
"""

import sys
import os
import pytest

# -----------------------------------------------------------------------------
# Path Configuration
# -----------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))


@pytest.fixture
def mock_config_dict() -> dict:
    """Returns a valid, complete configuration dictionary for testing (v1.1.1)."""
    return {
        "input_path": "/tmp/test",
        "output_base_dir": "/tmp/test",
        "output_subdir_name": "transcript",
        "output_prefix": "test_output",
        "process_modules": True,
        "process_tests": True,
        "create_individual_files": True,
        "create_unified_file": True,

        # Filters
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [],

        # Tree & AST
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "generate_tree": False,
        "print_tree": False,

        # Logging
        "save_error_log": True
    }