# tests/conftest.py
import sys
import os
import pytest

# -----------------------------------------------------------------------------
# Path Configuration
# -----------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

@pytest.fixture
def mock_config_dict():
    """Returns a valid, complete configuration dictionary for testing."""
    return {
        "input_path": "/tmp/test",
        "output_base_dir": "/tmp/test",
        "output_subdir_name": "transcript",
        "output_prefix": "test_output",
        "processing_mode": "todo",
        "extensiones": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [],
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "generate_tree": False,
        "print_tree": False,
        "save_error_log": True
    }