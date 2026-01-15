from __future__ import annotations

"""
Configuration Domain Management.

Handles persistent storage of application state, user preferences,
and profiles using JSON. Supports schema migration and default fallback.
"""

import json
import logging
import os
from typing import Any, Dict, List

from transcriptor4ai.infra.fs import DEFAULT_OUTPUT_SUBDIR, get_user_data_dir

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants & Defaults
# -----------------------------------------------------------------------------
CONFIG_FILE = os.path.join(get_user_data_dir(), "config.json")
DEFAULT_OUTPUT_PREFIX = "transcription"
CURRENT_CONFIG_VERSION = "2.0.0"

# Immutable default extension stacks for quick selection
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
    "Shell / Ops": [
        ".sh", ".bash", ".zsh", ".ps1", ".bat",
        "Dockerfile", ".dockerignore", ".yaml", ".yml"
    ],
    "Documentation": [".md", ".rst", ".txt", ".pdf"],
}

AI_MODELS: Dict[str, Dict[str, str]] = {
    "- Default Model -": {"id": "gpt-4o", "provider": "OPENAI"},
    "ChatGPT 4o": {"id": "chatgpt-4o-latest", "provider": "OPENAI"},
    "ChatGPT 5.2 (Preview)": {"id": "gpt-5.2-chat-latest", "provider": "OPENAI"},
    "Claude 3.5 Sonnet": {"id": "claude-3-5-sonnet-20240620", "provider": "ANTHROPIC"},
    "Gemini 1.5 Pro": {"id": "gemini-1.5-pro", "provider": "GOOGLE"},
    "Gemini 1.5 Flash": {"id": "gemini-1.5-flash", "provider": "GOOGLE"},
    "Llama 3 70B": {"id": "meta-llama/Meta-Llama-3-70B", "provider": "HF_LOCAL"},
    "Mistral Large": {"id": "mistral-large-latest", "provider": "MISTRAL"},
    "Mistral OCR": {"id": "mistral-ocr", "provider": "MISTRAL_VISION"},
    "DeepSeek V2": {"id": "deepseek-chat", "provider": "HF_LOCAL"},
}

DEFAULT_MODEL_KEY = "- Default Model -"


# -----------------------------------------------------------------------------
# Configuration Models (Dict-based)
# -----------------------------------------------------------------------------
def get_default_config() -> Dict[str, Any]:
    """
    Generate the default runtime configuration (Session State).
    This dictionary drives the behavior of the Pipeline.

    Returns:
        Dict[str, Any]: Default configuration values.
    """
    base = os.getcwd()
    return {
        # IO Paths
        "input_path": base,
        "output_base_dir": base,
        "output_subdir_name": DEFAULT_OUTPUT_SUBDIR,
        "output_prefix": DEFAULT_OUTPUT_PREFIX,

        # Content Selection
        "process_modules": True,
        "process_tests": True,
        "process_resources": True,

        # Output Format
        "create_individual_files": True,
        "create_unified_file": True,

        # Filtering
        "extensions": [".py"],
        "include_patterns": [".*"],
        "exclude_patterns": [
            r"^__init__\.py$",
            r".*\.pyc$",
            r"^(__pycache__|\.git|\.idea|\.vscode|node_modules)$",
            r"^\."
        ],
        "respect_gitignore": False,
        "target_model": DEFAULT_MODEL_KEY,

        # Analysis (Tree/AST)
        "generate_tree": True,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": True,

        # Optimization & Security
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # Diagnostics
        "save_error_log": False
    }


def get_default_app_state() -> Dict[str, Any]:
    """
    Generate the complete default application state structure.
    Includes global settings, profiles, and the last active session.

    Returns:
        Dict[str, Any]: The full JSON structure for config.json.
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
# Persistence Logic
# -----------------------------------------------------------------------------
def load_app_state() -> Dict[str, Any]:
    """
    Load application state from disk.
    Handles legacy schema migration automatically.

    Returns:
        Dict[str, Any]: The loaded state or a default structure on failure.
    """
    default_state = get_default_app_state()

    if not os.path.exists(CONFIG_FILE):
        logger.debug("Config file not found. Returning defaults.")
        return default_state

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            logger.warning("Corrupted config file. Resetting to defaults.")
            return default_state

        # V1.1 -> V1.2+ Migration Check
        if "input_path" in data:
            logger.info("Migrating legacy config schema...")
            new_state = get_default_app_state()
            new_state["last_session"].update(data)
            save_app_state(new_state)
            return new_state

        # Merge with defaults to ensure new keys exist
        state = default_state.copy()
        if "app_settings" in data:
            state["app_settings"].update(data["app_settings"])
        if "last_session" in data:
            state["last_session"].update(data["last_session"])
        if "saved_profiles" in data:
            state["saved_profiles"].update(data["saved_profiles"])
        if "custom_stacks" in data:
            state["custom_stacks"].update(data["custom_stacks"])

        # Update version stamp
        state["version"] = CURRENT_CONFIG_VERSION
        return state

    except Exception as e:
        logger.error(f"Failed to load config: {e}. Using defaults.")
        return default_state


def save_app_state(state: Dict[str, Any]) -> None:
    """
    Persist application state to disk.

    Args:
        state: The state dictionary to save.
    """
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        state["version"] = CURRENT_CONFIG_VERSION
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=4)
        logger.debug(f"Configuration saved to {CONFIG_FILE}")
    except OSError as e:
        logger.error(f"Failed to save configuration: {e}")


# -----------------------------------------------------------------------------
# Facade API
# -----------------------------------------------------------------------------
def load_config() -> Dict[str, Any]:
    """
    Retrieve the active configuration (Last Session) directly.
    """
    state = load_app_state()
    defaults = get_default_config()
    defaults.update(state.get("last_session", {}))
    return defaults


def save_config(config: Dict[str, Any]) -> None:
    """
    Save the provided config as the 'last_session'.
    """
    state = load_app_state()
    state["last_session"] = config
    save_app_state(state)