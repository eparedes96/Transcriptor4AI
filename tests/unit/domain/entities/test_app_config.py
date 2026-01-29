from __future__ import annotations

# ==============================================================================
# TEST GROUP: APP CONFIGURATION ENTITY
# ==============================================================================

import pytest
from typing import Any, Dict

from transcriptor4ai.domain.entities.app_config import (
    get_default_config,
    get_default_app_state,
    apply_config_integrity
)

# 1. ARRANGE: Shared constants for the test group
FAKE_PATH = "/path/to/project"


def test_get_default_config_completeness():
    """
    Ensures that the default configuration contains all critical keys
    required for the v2.1 pipeline execution.
    """
    # 2. ACT: Generate default configuration
    cfg = get_default_config(FAKE_PATH)

    # 3. ASSERT: Verify presence of mandatory schema keys
    required_keys = [
        "input_path", "output_base_dir", "output_subdir_name",
        "process_modules", "processing_depth", "process_tests",
        "create_individual_files", "create_unified_file",
        "target_model", "generate_tree", "enable_sanitizer"
    ]

    for key in required_keys:
        assert key in cfg, f"Missing mandatory key in default config: {key}"

    # Ensures path injection works
    assert cfg["input_path"] == FAKE_PATH
    assert cfg["output_base_dir"] == FAKE_PATH


def test_get_default_app_state_structure():
    """
    Verifies the root application state structure (config.json schema).
    """
    # 2. ACT
    state = get_default_app_state(FAKE_PATH)

    # 3. ASSERT
    assert "version" in state
    assert "app_settings" in state
    assert "last_session" in state
    assert "saved_profiles" in state
    assert isinstance(state["app_settings"], dict)
    assert state["last_session"]["input_path"] == FAKE_PATH


@pytest.mark.parametrize("initial_depth, process_modules, expected_depth", [
    ("full", False, "tree_only"),  # Case: Modules disabled, depth must degrade
    ("skeleton", False, "tree_only"),  # Case: Modules disabled in skeleton mode
    ("tree_only", False, "tree_only"),  # Case: Already consistent
])
def test_integrity_disabling_modules_forces_tree_only(initial_depth, process_modules, expected_depth):
    """
    Business Rule: If source logic (modules) is disabled,
    the processing depth MUST be 'tree_only'.
    """
    # 1. ARRANGE
    cfg = {
        "process_modules": process_modules,
        "processing_depth": initial_depth
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    # Ensures the depth is corrected to avoid processing files without logic
    assert cfg["processing_depth"] == expected_depth


def test_integrity_tree_only_depth_forces_no_modules():
    """
    Business Rule: If depth is explicitly set to 'tree_only',
    the 'process_modules' flag MUST be False to avoid logic extraction.
    """
    # 1. ARRANGE
    cfg = {
        "process_modules": True,
        "processing_depth": "tree_only"
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    # Synchronizes modules flag with the structural-only mode
    assert cfg["process_modules"] is False


def test_integrity_preserves_valid_config():
    """
    Ensures that a logically consistent configuration is not
    mutated by the integrity checker.
    """
    # 1. ARRANGE
    valid_cfg = {
        "process_modules": True,
        "processing_depth": "skeleton"
    }
    original_cfg = valid_cfg.copy()

    # 2. ACT
    apply_config_integrity(valid_cfg)

    # 3. ASSERT
    # No changes should occur for a valid state
    assert valid_cfg == original_cfg