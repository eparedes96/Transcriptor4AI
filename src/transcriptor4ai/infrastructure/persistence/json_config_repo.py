from __future__ import annotations

"""
JSON Configuration Repository.

Concrete implementation of the IConfigRepository port. Manages the persistence
of application state and user profiles using a local JSON file stored in the
user's data directory.

Integrates automatic schema migration logic to ensure backward compatibility
across application updates.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

from transcriptor4ai.domain.entities.app_config import get_default_app_state, get_default_config
from transcriptor4ai.domain.ports.config_port import IConfigRepository
from transcriptor4ai.infrastructure.persistence.migrations import run_migrations
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter
from transcriptor4ai.shared import constants as const

logger = logging.getLogger(__name__)


# ==============================================================================
# CONFIGURATION REPOSITORY IMPLEMENTATION
# ==============================================================================
class JsonConfigRepository(IConfigRepository):
    """
    Persistence adapter using a standard JSON file.
    """

    def __init__(self, fs_adapter: Optional[FileSystemAdapter] = None) -> None:
        """
        Initialize the repository.

        Args:
            fs_adapter: Optional filesystem adapter instance. If None, instantiates a new one.
        """
        self._fs = fs_adapter or FileSystemAdapter()
        self._config_path = os.path.join(self._fs.get_user_data_dir(), "config.json")

    # ==============================================================================
    # GLOBAL STATE MANAGEMENT
    # ==============================================================================
    def load_app_state(self) -> Dict[str, Any]:
        """
        Retrieve application state, applying migrations and schema validation.
        """
        # 1. SETUP: Prepare default state as fallback
        base_path = os.getcwd()
        default_state = get_default_app_state(base_path)

        if not os.path.exists(self._config_path):
            logger.debug("ConfigRepo: File absent. Initializing defaults.")
            return default_state

        try:
            # 2. READ: Load raw JSON content
            with open(self._config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if not isinstance(data, dict):
                logger.warning("ConfigRepo: Corruption detected. Resetting state.")
                return default_state

            # 3. MIGRATE: Upgrade legacy schemas if necessary
            data = run_migrations(data, default_state)

            # 4. MERGE: Ensure all keys exist (overlay loaded data onto defaults)
            state = default_state.copy()

            if "app_settings" in data:
                state["app_settings"].update(data["app_settings"])

            if "last_session" in data:
                state["last_session"].update(data["last_session"])

            if "saved_profiles" in data:
                state["saved_profiles"].update(data["saved_profiles"])

            if "custom_stacks" in data:
                state["custom_stacks"].update(data["custom_stacks"])

            # Force current version stamp
            state["version"] = const.CURRENT_CONFIG_VERSION
            return state

        except (OSError, json.JSONDecodeError) as e:
            logger.error(f"ConfigRepo: Load failure: {e}")
            return default_state

    def save_app_state(self, state: Dict[str, Any]) -> None:
        """
        Atomically persist the application state to disk.
        """
        try:
            # Update version stamp before saving
            state["version"] = const.CURRENT_CONFIG_VERSION

            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)

            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=4)

            logger.debug(f"ConfigRepo: State saved to {self._config_path}")

        except OSError as e:
            logger.error(f"ConfigRepo: Save failure: {e}")

    # ==========================================================================
    # SESSION CONFIGURATION SHORTCUTS
    # ==========================================================================
    def load_config(self) -> Dict[str, Any]:
        """Extract the 'last_session' configuration from the state."""
        state = self.load_app_state()

        # Merge with factory defaults to ensure integrity of new fields
        defaults = get_default_config(os.getcwd())
        defaults.update(state.get("last_session", {}))

        return defaults

    def save_config(self, config: Dict[str, Any]) -> None:
        """Update only the 'last_session' section of the state."""
        state = self.load_app_state()
        state["last_session"] = config
        self.save_app_state(state)

    # ==========================================================================
    # PROFILE MANAGEMENT (CRUD)
    # ==========================================================================
    def save_profile(self, name: str, config: Dict[str, Any]) -> None:
        """Store a configuration dictionary as a named profile."""
        state = self.load_app_state()

        if "saved_profiles" not in state:
            state["saved_profiles"] = {}

        state["saved_profiles"][name] = config
        self.save_app_state(state)
        logger.info(f"ConfigRepo: Profile '{name}' persisted.")

    def delete_profile(self, name: str) -> bool:
        """Remove a profile from persistence."""
        state = self.load_app_state()
        profiles = state.get("saved_profiles", {})

        if name in profiles:
            del profiles[name]
            self.save_app_state(state)
            logger.info(f"ConfigRepo: Profile '{name}' deleted.")
            return True

        return False

    def get_profile_names(self) -> List[str]:
        """List all available profile identifiers."""
        state = self.load_app_state()
        profiles = state.get("saved_profiles", {})
        return sorted(list(profiles.keys()))