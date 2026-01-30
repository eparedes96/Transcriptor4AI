# ==============================================================================
# TEST GROUP: JSON CONFIGURATION REPOSITORY (INTEGRATION)
# ==============================================================================

import json
import os
import pytest
from transcriptor4ai.infrastructure.persistence.json_config_repo import JsonConfigRepository
from transcriptor4ai.shared import constants as const


@pytest.fixture
def mock_fs(mocker, tmp_path):
    """
    Mocks the IFileSystem port to isolate the config file
    within a temporary sandbox.
    """
    fs = mocker.Mock()
    # Redirect config path to the pytest temp folder
    fs.get_user_data_dir.return_value = str(tmp_path)
    return fs


@pytest.fixture
def config_repo(mock_fs):
    """
    Provides a JsonConfigRepository instance with injected mock filesystem.
    """
    return JsonConfigRepository(fs_adapter=mock_fs)


@pytest.mark.integration
def test_json_config_initial_load_returns_defaults(config_repo):
    """
    Ensures that if no config file exists, the repository returns
    the valid default application state.
    """
    # 2. ACT
    state = config_repo.load_app_state()

    # 3. ASSERT
    assert state["version"] == const.CURRENT_CONFIG_VERSION
    assert "last_session" in state
    assert state["app_settings"]["locale"] == "en"


@pytest.mark.integration
def test_json_config_save_and_load_cycle(config_repo, mock_app_state):
    """
    Validates a complete write-read cycle of the application state.
    """
    # 1. ARRANGE
    mock_app_state["app_settings"]["theme"] = "Dark"
    mock_app_state["last_session"]["output_prefix"] = "custom_run"

    # 2. ACT
    config_repo.save_app_state(mock_app_state)
    loaded_state = config_repo.load_app_state()

    # 3. ASSERT
    assert loaded_state["app_settings"]["theme"] == "Dark"
    assert loaded_state["last_session"]["output_prefix"] == "custom_run"
    assert loaded_state["version"] == const.CURRENT_CONFIG_VERSION


@pytest.mark.integration
def test_json_config_profile_lifecycle(config_repo, mock_config_dict):
    """
    Verifies saving, listing, and deleting user configuration profiles.
    """
    # 1. ARRANGE: Define profiles
    profile_name = "PythonOptimization"
    mock_config_dict["extensions"] = [".py"]
    mock_config_dict["minify_output"] = True

    # 2. ACT: Save and retrieve
    config_repo.save_profile(profile_name, mock_config_dict)

    names = config_repo.get_profile_names()
    assert profile_name in names

    # 3. ACT: Delete
    deleted = config_repo.delete_profile(profile_name)
    assert deleted is True
    assert profile_name not in config_repo.get_profile_names()


@pytest.mark.integration
def test_json_config_migration_integration(mock_fs, tmp_path):
    """
    CRITICAL: Validates that the repository automatically migrates
    legacy schemas (v1.1) to the current version (v2.1) upon loading.
    """
    # 1. ARRANGE: Manually write a legacy-style config (v1.1 flat structure)
    config_path = tmp_path / "config.json"
    legacy_data = {
        "input_path": "/legacy/path",
        "process_modules": True,  # Legacy boolean
        "extensions": [".js"]
    }
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(legacy_data, f)

    # 2. ACT: Load via repository
    repo = JsonConfigRepository(fs_adapter=mock_fs)
    migrated_state = repo.load_app_state()

    # 3. ASSERT: Check v2.1 structure and mapping
    assert migrated_state["version"] == const.CURRENT_CONFIG_VERSION
    assert "last_session" in migrated_state

    # Verify migration logic was triggered (process_modules -> processing_depth)
    session = migrated_state["last_session"]
    assert session["input_path"] == "/legacy/path"
    assert session["processing_depth"] == "full"  # Auto-migrated


@pytest.mark.integration
def test_json_config_resilience_to_corruption(mock_fs, tmp_path):
    """
    Ensures the application defaults are returned if the JSON file
    on disk is malformed or corrupted.
    """
    # 1. ARRANGE: Create a non-JSON file
    config_path = tmp_path / "config.json"
    with open(config_path, "w") as f:
        f.write("INVALID { JSON [ DATA")

    # 2. ACT
    repo = JsonConfigRepository(fs_adapter=mock_fs)
    state = repo.load_app_state()

    # 3. ASSERT: Fallback to safe defaults instead of crashing
    assert state["version"] == const.CURRENT_CONFIG_VERSION
    assert isinstance(state["last_session"], dict)


@pytest.mark.integration
def test_json_config_atomic_save_config_helper(config_repo, mock_config_dict):
    """
    Validates the load_config/save_config shortcuts used by the CLI/GUI.
    """
    # 1. ARRANGE
    mock_config_dict["target_model"] = "claude-3-opus"

    # 2. ACT
    config_repo.save_config(mock_config_dict)
    loaded_cfg = config_repo.load_config()

    # 3. ASSERT
    assert loaded_cfg["target_model"] == "claude-3-opus"