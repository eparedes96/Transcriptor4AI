from __future__ import annotations

"""
Unit tests for the Config Domain.

Verifies:
1. Default configuration generation.
2. Resilience against corrupted config files.
3. Legacy schema migration logic (V1.1 -> +V1.2).
4. Persistence (Save/Load) without touching real user data.
"""

import json
import os
from unittest.mock import patch
import pytest

from transcriptor4ai.domain.config import (
    load_app_state,
    get_default_app_state,
    get_default_config
)
from transcriptor4ai.domain.constants import CURRENT_CONFIG_VERSION


@pytest.fixture
def mock_user_data_dir(tmp_path):
    """
    Fixture to mock the user data directory.
    Prevents tests from reading/writing to the real OS user folder.
    """
    # Create a temporary directory structure
    config_dir = tmp_path / "Transcriptor4AI"
    config_dir.mkdir()

    # Patch the fs helper to return this temp path
    with patch("transcriptor4ai.domain.config.get_user_data_dir", return_value=str(config_dir)):
        yield config_dir


def test_load_fresh_state_returns_defaults(mock_user_data_dir):
    """
    If no config file exists, it should return the default state structure.
    """
    # Ensure file does not exist
    config_path = mock_user_data_dir / "config.json"
    assert not config_path.exists()

    # Better approach: Patch the CONFIG_FILE variable directly in the module
    mock_file_path = str(config_path)
    with patch("transcriptor4ai.domain.config.CONFIG_FILE", mock_file_path):
        state = load_app_state()

        assert state["version"] == CURRENT_CONFIG_VERSION
        assert state["last_session"]["process_modules"] is True  # Default check


def test_load_corrupted_file_returns_defaults(mock_user_data_dir):
    """If JSON is malformed, it should fall back to defaults safely."""
    config_path = mock_user_data_dir / "config.json"
    config_path.write_text("{ incomplete json ", encoding="utf-8")

    with patch("transcriptor4ai.domain.config.CONFIG_FILE", str(config_path)):
        state = load_app_state()

        # Should reset to defaults
        assert state["version"] == CURRENT_CONFIG_VERSION
        assert isinstance(state["last_session"], dict)


def test_migration_v1_1_to_v1_6(mock_user_data_dir):
    """
    Verify that a legacy flat config file (V1.1) is correctly migrated
    to the new hierarchical structure inside 'last_session'.
    """
    legacy_config = {
        "input_path": "/legacy/path",
        "extensions": [".js"],
        "create_unified_file": False
    }

    config_path = mock_user_data_dir / "config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(legacy_config, f)

    with patch("transcriptor4ai.domain.config.CONFIG_FILE", str(config_path)):
        state = load_app_state()

        # Check structure update
        assert "last_session" in state
        assert "app_settings" in state
        assert state["version"] == CURRENT_CONFIG_VERSION

        # Check data preservation
        session = state["last_session"]
        assert session["input_path"] == "/legacy/path"
        assert session["extensions"] == [".js"]
        assert session["create_unified_file"] is False

        # Check merged defaults (new keys should be present)
        assert "process_modules" in session


def test_get_default_config_completeness():
    """Ensure default config contains all critical keys."""
    defaults = get_default_config()

    keys = [
        "input_path", "output_base_dir", "process_modules",
        "create_unified_file", "extensions", "target_model",
        "enable_sanitizer"
    ]

    for k in keys:
        assert k in defaults