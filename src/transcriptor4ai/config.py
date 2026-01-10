from __future__ import annotations

"""
Configuration management for transcriptor4ai.

Handles persistent storage in JSON with support for:
- Application Settings (Global)
- Session Persistence (Last state)
- User Profiles
- Extension Stacks
- Legacy Migration
"""

import json
import logging
import os
from typing import Any, Dict, List

from transcriptor4ai.paths import DEFAULT_OUTPUT_SUBDIR, get_user_data_dir

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
CONFIG_FILE = os.path.join(get_user_data_dir(), "config.json")
DEFAULT_OUTPUT_PREFIX = "transcription"
CURRENT_CONFIG_VERSION = "1.4.0"

# Predefined Extension Stacks (Immutable defaults)
DEFAULT_STACKS: Dict[str, List[str]] = {
    "Python Data": [".py", ".ipynb", ".json", ".csv", ".yaml"],
    "Web Fullstack": [".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"],
    "Java/Kotlin": [".java", ".kt", ".kts", ".xml", ".gradle", ".properties"],
    "C# / .NET": [".cs", ".csproj", ".sln", ".xml", ".config", ".json"],
    "C / C++": [".c", ".cpp", ".h", ".hpp", "CMakeLists.txt", "Makefile"],
    "Mobile (Swift/Dart)": [".swift", ".dart", ".yaml", ".xml", ".plist"],
    "Rust": [".rs", ".toml"],
    "Go": [".go", ".mod", ".sum"],
    "PHP Legacy": [".php", ".phtml", "composer.json", ".ini"],
    "Shell / Ops": [".sh", ".bash", ".zsh", ".ps1", ".bat", "Dockerfile", ".dockerignore", ".yaml", ".yml"],
    "Documentation": [".md", ".rst", ".txt", ".pdf"],
}


# -----------------------------------------------------------------------------
# Configuration: Defaults (Runtime Flat Config)
# -----------------------------------------------------------------------------
def get_default_config() -> Dict[str, Any]:
    """
    Return the default runtime configuration dictionary (Session State).
    Used by CLI and Pipeline logic.
    """
    base = os.getcwd()
    return {
        "input_path": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": DEFAULT_OUTPUT_PREFIX,

        # Content Selection (Granular)
        "process_modules": True,
        "process_tests": True,
        "process_resources": False,

        # Output Format Selection
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
        "respect_gitignore": True,

        "target_model": "GPT-4o / GPT-5",

        # Tree & AST Options
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "generate_tree": False,
        "print_tree": True,

        # Optimization & Privacy
        "enable_sanitizer": True,
        "mask_user_paths": True,
        "minify_output": False,

        # Logging
        "save_error_log": True
    }


def get_default_app_state() -> Dict[str, Any]:
    """
    Return the full default JSON structure.
    Includes settings, last session, profiles, and custom stacks.
    """
    return {
        "version": CURRENT_CONFIG_VERSION,
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


# -----------------------------------------------------------------------------
# I/O Operations: Full State Management
# -----------------------------------------------------------------------------
def load_app_state() -> Dict[str, Any]:
    """
    Load the complete application state from 'config.json'.
    Handles auto-migration from V1.1 (flat) to V1.2+ (hierarchical).
    """
    default_state = get_default_app_state()

    if not os.path.exists(CONFIG_FILE):
        logger.debug("No config file found. Using default state.")
        return default_state

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Invalid config format. Resetting to defaults.")
            return default_state

        # --- MIGRATION LOGIC (V1.1 -> V1.2+) ---
        if "input_path" in data:
            logger.info("Detected Legacy V1.1 Config. Migrating to V1.2+ structure...")
            new_state = get_default_app_state()
            new_state["last_session"].update(data)
            save_app_state(new_state)
            return new_state

        # --- NORMAL LOAD & KEY MERGING ---
        state = default_state.copy()

        # Merge sub-dictionaries
        if "app_settings" in data:
            state["app_settings"].update(data["app_settings"])
        if "last_session" in data:
            state["last_session"].update(data["last_session"])
        if "saved_profiles" in data:
            state["saved_profiles"].update(data["saved_profiles"])
        if "custom_stacks" in data:
            state["custom_stacks"].update(data["custom_stacks"])

        state["version"] = CURRENT_CONFIG_VERSION

        return state

    except Exception as e:
        logger.error(f"Failed to load app state: {e}. Returning defaults.")
        return default_state


def save_app_state(state: Dict[str, Any]) -> None:
    """Save the complete application state to 'config.json'."""
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        state["version"] = CURRENT_CONFIG_VERSION
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logger.debug(f"App state saved to {CONFIG_FILE}")
    except OSError as e:
        logger.error(f"Failed to save app state: {e}")


# -----------------------------------------------------------------------------
# Legacy/Convenience API (Maintains compatibility with Main/CLI/GUI)
# -----------------------------------------------------------------------------
def load_config() -> Dict[str, Any]:
    """
    Load the active runtime configuration (Last Session).

    This acts as a facade so CLI/GUI don't need to know about
    the complex hierarchical JSON structure immediately.
    """
    state = load_app_state()
    defaults = get_default_config()
    defaults.update(state.get("last_session", {}))
    return defaults


def save_config(config: Dict[str, Any]) -> None:
    """
    Save the given config dict as the 'last_session' in the full state file.
    """
    state = load_app_state()
    state["last_session"] = config
    save_app_state(state)