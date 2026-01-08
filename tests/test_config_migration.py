from __future__ import annotations

"""
Unit tests for Configuration Migration logic (V1.1 -> V1.2).
"""

import json
import os
import pytest
from transcriptor4ai.config import load_app_state, get_default_app_state


def test_migration_v1_1_to_v1_2(tmp_path):
    """
    Verify that a legacy flat config file is correctly migrated
    to the new hierarchical structure inside 'last_session'.
    """
    # 1. Simulate a V1.1 Legacy Config File
    legacy_config = {
        "input_path": "/legacy/path",
        "extensions": [".js"],
        "create_unified_file": False
    }

    # Mock the config file location
    config_file = tmp_path / "config.json"
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(legacy_config, f)

    # Monkeypatching the CONFIG_FILE path inside the module for this test
    import transcriptor4ai.config as cfg
    orig_file = cfg.CONFIG_FILE
    cfg.CONFIG_FILE = str(config_file)

    try:
        # 2. Perform Load (triggers migration)
        state = load_app_state()

        # 3. Assertions
        assert "last_session" in state
        assert "app_settings" in state

        # Check data preservation
        session = state["last_session"]
        assert session["input_path"] == "/legacy/path"
        assert session["extensions"] == [".js"]
        assert session["create_unified_file"] is False

        # Check defaults were merged
        assert "process_modules" in session

    finally:
        cfg.CONFIG_FILE = orig_file


def test_load_fresh_v1_2_state(tmp_path):
    """Verify loading a fresh state returns defaults if file missing."""
    import transcriptor4ai.config as cfg
    orig_file = cfg.CONFIG_FILE
    cfg.CONFIG_FILE = str(tmp_path / "non_existent.json")

    try:
        state = load_app_state()
        assert state["version"] == "1.2.0"
        assert state["last_session"]["process_resources"] is False
    finally:
        cfg.CONFIG_FILE = orig_file