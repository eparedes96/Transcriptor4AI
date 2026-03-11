from __future__ import annotations

from typing import Any, Dict

import pytest

from transcriptor4ai.infrastructure.persistence.migrations import run_migrations

# ==============================================================================
# TEST GROUP: SCHEMA MIGRATIONS LOGIC
# ==============================================================================

@pytest.fixture
def default_state() -> Dict[str, Any]:
    """
    1. ARRANGE: Provides a standard v2.1 application state scaffold.
    Used by the migrator to construct missing nested structures.
    """
    return {
        "version": "2.1.0",
        "app_settings": {"theme": "System"},
        "last_session": {"input_path": "", "processing_depth": "full"},
        "saved_profiles": {}
    }


@pytest.mark.integration
def test_migrates_v1_flat_schema_to_v2_nested_structure(default_state):
    """
    Verifies that v1.1 flat JSONs (where settings were at the root)
    are properly encapsulated into the 'last_session' nested block.
    """
    # 1. ARRANGE: Create a legacy v1.1 configuration dictionary
    legacy_v1_data = {
        "input_path": "/legacy/project/path",
        "extensions": [".py"],
        "process_modules": False  # Should also trigger the secondary migration
    }

    # 2. ACT: Execute the migration chain
    migrated_data = run_migrations(legacy_v1_data, default_state)

    # 3. ASSERT: Structure is normalized and values preserved
    assert "last_session" in migrated_data
    assert migrated_data["last_session"]["input_path"] == "/legacy/project/path"
    assert migrated_data["last_session"]["extensions"] == [".py"]

    # Verify the secondary migration (process_modules -> processing_depth) also fired
    assert migrated_data["last_session"]["processing_depth"] == "tree_only"


@pytest.mark.integration
@pytest.mark.parametrize("process_modules_flag, expected_depth", [
    (True, "full"),
    (False, "tree_only")
])
def test_migrates_legacy_process_modules_flag_to_processing_depth_enum(
        default_state,
        process_modules_flag,
        expected_depth
):
    """
    Ensures that the v2.0 boolean 'process_modules' is correctly translated
    into the v2.1 'processing_depth' enum across all relevant configuration blocks.
    """
    # 1. ARRANGE: v2.0 structure with legacy flags
    legacy_v2_data = {
        "last_session": {
            "process_modules": process_modules_flag
        },
        "saved_profiles": {
            "Profile A": {"process_modules": process_modules_flag},
            "Profile B": {"process_modules": not process_modules_flag}  # Inverse case
        }
    }

    # 2. ACT: Execute migration
    migrated_data = run_migrations(legacy_v2_data, default_state)

    # 3. ASSERT: Flags translated in last_session
    assert migrated_data["last_session"]["processing_depth"] == expected_depth

    # ASSERT: Flags translated in saved profiles
    expected_profile_b_depth = "tree_only" if process_modules_flag else "full"
    assert migrated_data["saved_profiles"]["Profile A"]["processing_depth"] == expected_depth
    assert migrated_data["saved_profiles"]["Profile B"]["processing_depth"] == expected_profile_b_depth


@pytest.mark.integration
def test_migration_is_idempotent_on_current_schema(default_state):
    """
    Validates that providing an already modern (v2.1) configuration
    does not alter or damage the data (Idempotency).
    """
    # 1. ARRANGE: A perfect modern config
    modern_data = {
        "version": "2.1.0",
        "last_session": {
            "input_path": "/modern/path",
            "processing_depth": "skeleton",  # Explicit modern enum
            "process_modules": True  # Even if present, it shouldn't override depth
        }
    }

    # 2. ACT
    migrated_data = run_migrations(modern_data, default_state)

    # 3. ASSERT: The modern 'processing_depth' is preserved exactly as it was
    assert migrated_data["last_session"]["processing_depth"] == "skeleton"
    assert migrated_data["last_session"]["input_path"] == "/modern/path"


@pytest.mark.integration
def test_migration_handles_missing_sections_gracefully(default_state):
    """
    Ensures that corrupted or completely empty dictionaries don't crash
    the migrator via KeyErrors.
    """
    # 1. ARRANGE: Missing 'last_session' and 'saved_profiles' completely
    corrupted_data = {"random_key": "unrelated_data"}

    # 2. ACT: Execute migration
    # Should safely extract .get("last_session", {}) and do nothing
    migrated_data = run_migrations(corrupted_data, default_state)

    # 3. ASSERT: No crash occurred, unrelated keys are preserved
    assert "random_key" in migrated_data