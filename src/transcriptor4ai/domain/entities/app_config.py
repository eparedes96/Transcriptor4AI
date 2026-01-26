from __future__ import annotations

"""
Configuration Domain Entities.

Defines the core data structures and integrity rules for the application 
state and session configuration. This module implements the "Domain Model" 
pattern, centralizing business logic validation.
"""

import os
from typing import Any, Dict

from transcriptor4ai.shared import constants as const

# ==============================================================================
# DOMAIN CONSTANTS
# ==============================================================================
DEFAULT_OUTPUT_SUBDIR = "transcript"

# ==============================================================================
# CONFIGURATION FACTORIES (PUBLIC API)
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
        "process_modules": True,  # Legacy toggle
        "processing_depth": "full",  # Strategy: "full", "skeleton", "tree_only"
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


# ==============================================================================
# DOMAIN LOGIC: INTEGRITY RULES
# ==============================================================================

def apply_config_integrity(cfg: Dict[str, Any]) -> None:
    """
    Enforce business rules to ensure logical consistency within the config.

    This function modifies the dictionary in-place to prevent invalid
    combinations of processing flags.

    Rules:
    1. If source logic (modules) is disabled, depth must be 'tree_only'.
    2. If depth is 'tree_only', the modules flag must be False.
    """
    # 1. PROCESS: Evaluate module targeting against processing depth
    process_modules = cfg.get("process_modules", True)
    depth = cfg.get("processing_depth", "full")

    # Rule A: modules=False forces depth='tree_only'
    if not process_modules and depth != "tree_only":
        cfg["processing_depth"] = "tree_only"

    # Rule B: depth='tree_only' forces modules=False
    if depth == "tree_only":
        cfg["process_modules"] = False