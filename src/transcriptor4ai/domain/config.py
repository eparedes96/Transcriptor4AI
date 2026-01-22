from __future__ import annotations

"""
Configuration Domain Management.

Handles the persistent storage of application state, user preferences,
and session profiles using JSON serialization.
Delegates schema versioning logic to the migrations module.
"""

import json
import logging
import os
from typing import Any, Dict

from transcriptor4ai.domain import constants as const
from transcriptor4ai.domain.migrations import run_migrations
from transcriptor4ai.infra.fs import DEFAULT_OUTPUT_SUBDIR, get_user_data_dir

logger = logging.getLogger(__name__)

CONFIG_FILE = os.path.join(get_user_data_dir(), "config.json")

def get_default_config() -> Dict[str, Any]:
    """
    Generate the default execution configuration for a transcription session.

    This dictionary controls the behavior of the core pipeline, including
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

def load_app_state() -> Dict[str, Any]:
    """
    Retrieve application state from persistent storage.

    Delegates schema migration to the migrations module to ensure
    compatibility across versions (v1.1 -> v2.0+).

    Returns:
        Dict[str, Any]: The loaded state dictionary.
    """
    default_state = get_default_app_state()

    if not os.path.exists(CONFIG_FILE):
        logger.debug("Config file absent. Initializing with defaults.")
        return default_state

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Configuration corruption detected. Resetting state.")
            return default_state

        # Delegate migration logic
        data = run_migrations(data, default_state)

        # Merge with defaults to ensure missing keys are populated
        state = default_state.copy()
        if "app_settings" in data:
            state["app_settings"].update(data["app_settings"])
        if "last_session" in data:
            state["last_session"].update(data["last_session"])
        if "saved_profiles" in data:
            state["saved_profiles"].update(data["saved_profiles"])
        if "custom_stacks" in data:
            state["custom_stacks"].update(data["custom_stacks"])

        state["version"] = const.CURRENT_CONFIG_VERSION
        return state

    except Exception as e:
        logger.error(f"Failed to decode configuration file: {e}")
        return default_state

def save_app_state(state: Dict[str, Any]) -> None:
    """
    Persist the application state dictionary to disk.

    Args:
        state: The state dictionary to serialize and save.
    """
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        state["version"] = const.CURRENT_CONFIG_VERSION
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logger.debug(f"State successfully persisted to {CONFIG_FILE}")
    except OSError as e:
        logger.error(f"I/O error while saving configuration: {e}")

def load_config() -> Dict[str, Any]:
    """
    Extract the active session configuration from the application state.

    Returns:
        Dict[str, Any]: The most recently used session configuration.
    """
    state = load_app_state()
    defaults = get_default_config()
    defaults.update(state.get("last_session", {}))
    return defaults

def save_config(config: Dict[str, Any]) -> None:
    """
    Update and persist the provided config as the 'last_session' state.

    Args:
        config: The session configuration to save.
    """
    state = load_app_state()
    state["last_session"] = config
    save_app_state(state)