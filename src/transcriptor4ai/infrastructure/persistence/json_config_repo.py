from __future__ import annotations

import json
import os
from typing import Dict, Any

from transcriptor4ai.domain.entities.app_config import get_default_app_state, CONFIG_FILE, logger, get_default_config
from transcriptor4ai.infrastructure.persistence.migrations import run_migrations
from transcriptor4ai.shared import constants as const


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
