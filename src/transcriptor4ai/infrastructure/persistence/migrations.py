from __future__ import annotations

"""
Schema Migration Service.

Provides a chain-of-responsibility mechanism to upgrade legacy configuration
dictionaries to the latest schema version. This module contains pure logic
transformations and does not perform I/O operations.
"""

import logging
import copy
from typing import Any, Dict

logger = logging.getLogger(__name__)


# ==============================================================================
# MIGRATION ORCHESTRATOR
# ==============================================================================
def run_migrations(data: Dict[str, Any], default_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the sequence of schema upgrades on the loaded configuration.

    Guarantees that the returned dictionary matches the current application
    state structure, preserving user data from older versions.

    Args:
        data: The raw dictionary loaded from the persistence layer (JSON).
        default_state: A clean instance of the current version's default state.

    Returns:
        Dict[str, Any]: The fully migrated and normalized state dictionary.
    """
    # 1. MIGRATION: V1.1 (Flat) -> V2.1 (Hierarchical)
    # Context: Older versions stored config keys at the root level.
    if "input_path" in data and "last_session" not in data:
        logger.info("Migrations: Detected legacy v1.1 schema. Upgrading to v2.1...")

        migrated = copy.deepcopy(default_state)
        migrated["last_session"].update(data)
        data = migrated

    # 2. MIGRATION: V2.0 (Boolean flags) -> V2.1 (Enum Strategy)
    # Context: 'process_modules' bool flag replaced by 'processing_depth' enum.
    _migrate_to_processing_depth(data)

    return data


# ==============================================================================
# MIGRATION STRATEGIES (PRIVATE)
# ==============================================================================
def _migrate_to_processing_depth(data: Dict[str, Any]) -> None:
    """
    Transform legacy boolean flags into the new 'processing_depth' enumeration.

    Migration Rules:
    - process_modules=True  -> processing_depth="full" (si no existe ya un valor más específico)
    - process_modules=False -> processing_depth="tree_only" (siempre prioriza deshabilitar módulos)

    Args:
        data: The state dictionary (mutable) to migrate in-place.
    """

    def _convert_and_cleanup(config_block: Dict[str, Any]) -> None:
        """Helper to mutate the block and remove the legacy key."""
        if "process_modules" in config_block:
            is_full = config_block.get("process_modules", True)

            # If no depth is defined, or if the flag forces "tree_only", we migrate
            if "processing_depth" not in config_block or not is_full:
                new_depth = "full" if is_full else "tree_only"

                # We only overwrite if it's 'tree_only' or if we didn't have depth (avoid deleting 'skeleton')
                if config_block.get("processing_depth") != "skeleton":
                    config_block["processing_depth"] = new_depth
                    logger.info(f"Migrations: converted process_modules={is_full} to {new_depth}")

            # Remove legacy key to prevent further migrations
            del config_block["process_modules"]

    # 1. PROCESS: Migrate active session state
    if "last_session" in data:
        _convert_and_cleanup(data["last_session"])

    # 2. PROCESS: Migrate all saved user profiles
    profiles = data.get("saved_profiles", {})
    if isinstance(profiles, dict):
        for name, profile in profiles.items():
            if isinstance(profile, dict):
                _convert_and_cleanup(profile)