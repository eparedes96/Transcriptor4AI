from __future__ import annotations

"""
Schema Migration Service.

Provides a chain-of-responsibility mechanism to upgrade legacy configuration
dictionaries to the latest schema version. This module contains pure logic
transformations and does not perform I/O operations.
"""

import logging
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
    # 1. MIGRATION: V1.1 (Flat) -> V2.0 (Hierarchical)
    # Context: Older versions stored config keys at the root level.
    if "input_path" in data:
        logger.info("Migrations: Detected legacy v1.1 schema. Upgrading to v2.0...")
        new_state = default_state.copy()

        # Ingest legacy root keys into the 'last_session' container
        new_state["last_session"].update(data)
        data = new_state

    # 2. MIGRATION: V2.0 (Boolean) -> V2.1 (Enum Strategy)
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
    - process_modules=True  -> processing_depth="full"
    - process_modules=False -> processing_depth="tree_only"

    Args:
        data: The state dictionary (mutable) to migrate in-place.
    """
    # 1. PROCESS: Migrate active session state
    last_sess = data.get("last_session", {})
    if "process_modules" in last_sess and "processing_depth" not in last_sess:
        is_full = last_sess.get("process_modules", True)
        depth = "full" if is_full else "tree_only"

        last_sess["processing_depth"] = depth
        logger.info(
            f"Migrations: last_session process_modules={is_full} -> processing_depth={depth}"
        )

    # 2. PROCESS: Migrate all saved user profiles
    profiles = data.get("saved_profiles", {})
    for name, profile in profiles.items():
        if "process_modules" in profile and "processing_depth" not in profile:
            is_full = profile.get("process_modules", True)
            depth = "full" if is_full else "tree_only"

            profile["processing_depth"] = depth
            logger.info(
                f"Migrations: Profile '{name}' process_modules={is_full} -> depth={depth}"
            )