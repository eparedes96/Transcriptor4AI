from __future__ import annotations

"""
Global Pytest Configuration and Shared Fixtures.

Defines common data structures and mock objects for the Transcriptor4AI 
testing suite, ensuring consistency across Unit and Integration levels.
"""

import pytest
from typing import Any, Dict


# ==============================================================================
# CONFIGURATION FIXTURES (DOMAIN ENTITIES)
# ==============================================================================

@pytest.fixture
def mock_config_dict() -> Dict[str, Any]:
    """
    Returns a complete and valid configuration dictionary for v2.1.

    Reflects the domain entity structure used in the pipeline and 
    configuration repositories.
    """
    return {
        # Path Configuration
        "input_path": "/tmp/fake_project",
        "output_base_dir": "/tmp/output",
        "output_subdir_name": "transcript",
        "output_prefix": "test_prefix",

        # Processing Logic
        "processing_depth": "full",  # Options: "full", "skeleton", "tree_only"
        "process_modules": True,
        "process_tests": True,
        "process_resources": False,

        # Output Strategies
        "create_individual_files": True,
        "create_unified_file": True,

        # Filters & Regex
        "extensions": [".py", ".js"],
        "include_patterns": [".*"],
        "exclude_patterns": [r"__pycache__", r"\.git"],
        "respect_gitignore": True,

        # AI & Economic Metrics
        "target_model": "gpt-4o",

        # Static Analysis (AST)
        "generate_tree": True,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": False,

        # Optimization & Privacy
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # Logging & Diagnostics
        "save_error_log": True
    }


@pytest.fixture
def mock_app_state(mock_config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates the global application state structure (config.json).
    """
    return {
        "version": "2.1.0",
        "app_settings": {
            "theme": "System",
            "locale": "en",
            "allow_telemetry": False,
            "auto_check_updates": False
        },
        "last_session": mock_config_dict,
        "saved_profiles": {
            "Default": mock_config_dict
        },
        "custom_stacks": {}
    }


# ==============================================================================
# INFRASTRUCTURE MOCKS (PORTS)
# ==============================================================================

@pytest.fixture
def mock_user_context(mocker: Any) -> Any:
    """
    Mock for the IUserContext port to provide deterministic paths.
    """
    mock = mocker.Mock()
    mock.get_username.return_value = "test_user"
    mock.get_home_directory.return_value = "/home/test_user"
    return mock