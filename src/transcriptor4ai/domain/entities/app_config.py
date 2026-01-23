from __future__ import annotations

"""
Configuration Domain Entities.

Defines the default data structures and schemas for the application state
and session configuration. This module is pure data definition and does
not handle I/O or persistence.
"""

import os
from typing import Any, Dict

from transcriptor4ai.shared import constants as const

# ==============================================================================
# DOMAIN CONSTANTS
# ==============================================================================
DEFAULT_OUTPUT_SUBDIR = "transcript"

# ==============================================================================
# CONFIGURATION FACTORIES
# ==============================================================================
def get_default_config(base_path: str) -> Dict[str, Any]:
    """
    Generate the default execution configuration for a transcription session.

    This dictionary controls the behavior of the application pipeline, including
    I/O paths, filtering rules, and optimization flags.

    Args:
        base_path: The filesystem path to use as root for input and output.

    Returns:
        Dict[str, Any]: Default session configuration values.
    """
    return {
        # IO Settings
        "input_path": base_path,
        "output_base_dir": base_path,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": const.DEFAULT_OUTPUT_PREFIX,

        # Scope Settings (v2.1+ Schema)
        "process_modules": True,  # Kept for backward compatibility
        "processing_depth": "full",  # Options: "full", "skeleton", "tree_only"
        "process_tests": True,
        "process_resources": True,

        # Output Structure
        "create_individual_files": True,
        "create_unified_file": True,

        # Filters
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [
            r"^__init__\.py$",
            r".*\.pyc$",
            r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
            r"^\."
        ],
        "respect_gitignore": False,
        "target_model": const.DEFAULT_MODEL_KEY,

        # Analysis & Tree
        "generate_tree": True,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": True,

        # Privacy & Optimization
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # Diagnostics
        "save_error_log": False
    }

def get_default_app_state(base_path: str) -> Dict[str, Any]:
    """
    Generate the complete root application state structure.

    Encapsulates global application settings, user-defined profiles,
    and the state of the last active session for persistence.

    Args:
        base_path: The filesystem path to use for the initial session.

    Returns:
        Dict[str, Any]: The full application state schema.
    """
    return {
        "version": const.CURRENT_CONFIG_VERSION,
        "app_settings": {
            "theme": "SystemDefault",
            "locale": "en",
            "allow_telemetry": True,
            "auto_check_updates": True,
            "last_update_check": ""
        },
        "last_session": get_default_config(base_path),
        "saved_profiles": {},
        "custom_stacks": {}
    }