from __future__ import annotations

"""
Configuration Domain Management.

Handles the persistent storage of application state, user preferences,
and session profiles using JSON serialization.
Delegates schema versioning logic to the migrations module.
"""

import logging
import os
from typing import Any, Dict

from transcriptor4ai.shared import constants as const
from transcriptor4ai.infrastructure.system.os_file_system import get_user_data_dir, DEFAULT_OUTPUT_SUBDIR

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(get_user_data_dir(), "config.json")

def get_default_config() -> Dict[str, Any]:
    """
    Generate the default execution configuration for a transcription session.

    This dictionary controls the behavior of the application pipeline, including
    I/O paths, filtering rules, and optimization flags.

    Returns:
        Dict[str, Any]: Default session configuration values.
    """
    base = os.getcwd()
    return {
        # IO Settings
        "input_path": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": const.DEFAULT_OUTPUT_PREFIX,

        # Scope Settings (v2.1+ Schema)
        "process_modules": True,  # Kept for backward compatibility
        "processing_depth": "full",
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

def get_default_app_state() -> Dict[str, Any]:
    """
    Generate the complete root application state structure.

    Encapsulates global application settings, user-defined profiles,
    and the state of the last active session for persistence.

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
        "last_session": get_default_config(),
        "saved_profiles": {},
        "custom_stacks": {}
    }