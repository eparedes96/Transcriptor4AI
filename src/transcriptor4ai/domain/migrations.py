from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

def run_migrations(data: Dict[str, Any], default_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrate the migration of legacy configuration schemas to the current version.

    Applies a chain of responsibility to transform raw loaded JSON into a
    structure compatible with the current application state.

    Args:
        data: The raw dictionary loaded from config.json.
        default_state: A clean instance of the current version's default state.

    Returns:
        Dict[str, Any]: The fully migrated and normalized state dictionary.
    """
    # 1. Migration: Flat Schema (v1.1) -> Hierarchical Schema (v2.0)
    # Detection: 'input_path' exists at root level
    if "input_path" in data:
        logger.info("Migrations: Detected legacy v1.1 schema. Upgrading to v2.0...")
        new_state = default_state.copy()
        # Merge root keys into 'last_session'
        new_state["last_session"].update(data)
        data = new_state

    # 2. Migration: Boolean Flags -> Processing Depth Enum (v2.1)
    # Detection: Handled inside the helper
    _migrate_to_processing_depth(data)

    return data

def _migrate_to_processing_depth(data: Dict[str, Any]) -> None:
    """
    Migrate legacy 'process_modules' boolean to 'processing_depth' enum.

    Handles the transition for last_session and all saved_profiles.
    Migration Logic:
        True -> "full"
        False -> "tree_only"

    Args:
        data: The state dictionary to migrate in-place.
    """
    # Migrate active session
    last_sess = data.get("last_session", {})
    if "process_modules" in last_sess and "processing_depth" not in last_sess:
        is_full = last_sess.get("process_modules", True)
        depth = "full" if is_full else "tree_only"
        last_sess["processing_depth"] = depth
        logger.info(
            f"Migrations: last_session process_modules={is_full} -> processing_depth={depth}"
        )

    # Migrate saved profiles
    profiles = data.get("saved_profiles", {})
    for name, profile in profiles.items():
        if "process_modules" in profile and "processing_depth" not in profile:
            is_full = profile.get("process_modules", True)
            depth = "full" if is_full else "tree_only"
            profile["processing_depth"] = depth
            logger.info(
                f"Migrations: Profile '{name}' process_modules={is_full} -> depth={depth}"
            )