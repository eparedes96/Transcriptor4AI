# ==============================================================================
# TEST GROUP: JSON CONFIGURATION REPOSITORY (INTEGRATION)
# ==============================================================================

import json
import shutil
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
    # Redirect config path to the pytest temp folder for atomic isolation
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
    the valid default application state defined in the domain.
    """
    # 1. ARRANGE: No file created in tmp_path

    # 2. ACT: Execute load
    state = config_repo.load_app_state()

    # 3. ASSERT: Verify initial state integrity
    assert state["version"] == const.CURRENT_CONFIG_VERSION
    assert "last_session" in state
    assert state["app_settings"]["locale"] == "en"


@pytest.mark.integration
def test_json_config_save_and_load_cycle(config_repo, mock_app_state):
    """
    Validates a complete write-read cycle of the application state
    to ensure serialization doesn't lose data.
    """
    # 1. ARRANGE: Prepare custom state
    mock_app_state["app_settings"]["theme"] = "Dark"
    mock_app_state["last_session"]["output_prefix"] = "custom_run"

    # 2. ACT: Persist and reload
    config_repo.save_app_state(mock_app_state)
    loaded_state = config_repo.load_app_state()

    # 3. ASSERT: Compare values
    assert loaded_state["app_settings"]["theme"] == "Dark"
    assert loaded_state["last_session"]["output_prefix"] == "custom_run"
    assert loaded_state["version"] == const.CURRENT_CONFIG_VERSION


@pytest.mark.integration
def test_json_config_profile_lifecycle(config_repo, mock_config_dict):
    """
    Verifies the CRUD-like lifecycle of configuration profiles
    (Save, List, Delete).
    """
    # 1. ARRANGE: Define target profile
    profile_name = "PythonOptimization"
    mock_config_dict["extensions"] = [".py"]
    mock_config_dict["minify_output"] = True

    # 2. ACT: Save and check existence
    config_repo.save_profile(profile_name, mock_config_dict)
    names = config_repo.get_profile_names()

    # 3. ASSERT: Verify persistence and cleanup
    assert profile_name in names

    deleted = config_repo.delete_profile(profile_name)
    assert deleted is True
    assert profile_name not in config_repo.get_profile_names()


@pytest.mark.integration
def test_json_config_migration_integration(mock_fs, tmp_path, static_assets_path):
    """
    CRITICAL: Validates that the repository correctly migrates legacy_v1.json
    (v1.1.0) into a v2.1 compatible structure upon load.
    """
    # 1. ARRANGE: Copy real legacy asset to the repository's target path
    legacy_source = static_assets_path / "configs" / "legacy_v1.json"
    target_config = tmp_path / "config.json"
    shutil.copy(legacy_source, target_config)

    # 2. ACT: Initialize repo and trigger load/migration
    repo = JsonConfigRepository(fs_adapter=mock_fs)
    migrated_state = repo.load_app_state()

    # 3. ASSERT: Verify schema upgrade and data preservation
    assert migrated_state["version"] == const.CURRENT_CONFIG_VERSION
    session = migrated_state["last_session"]

    # In legacy_v1.json, 'process_modules' is False.
    # Migration must map this to 'tree_only' depth.
    assert session["input_path"] == "/old/project/path"
    assert session["processing_depth"] == "tree_only"


@pytest.mark.integration
def test_json_config_resilience_to_corruption(mock_fs, tmp_path, static_assets_path):
    """
    Ensures that malformed files (corrupted.json) trigger a safe
    fallback to defaults instead of crashing the bootstrapping process.
    """
    # 1. ARRANGE: Inyect the corrupted JSON artifact
    corrupted_source = static_assets_path / "configs" / "corrupted.json"
    target_config = tmp_path / "config.json"
    shutil.copy(corrupted_source, target_config)

    # 2. ACT: Attempt load
    repo = JsonConfigRepository(fs_adapter=mock_fs)
    state = repo.load_app_state()

    # 3. ASSERT: System should recover using domain defaults
    # Ensures the app starts even if the config file is unreadable
    assert state["version"] == const.CURRENT_CONFIG_VERSION
    assert isinstance(state["last_session"], dict)
    assert state["last_session"]["processing_depth"] == "full"


@pytest.mark.integration
def test_json_config_atomic_save_config_helper(config_repo, mock_config_dict):
    """
    Validates the load_config/save_config shortcuts, ensuring they
    synchronize with the underlying session state.
    """
    # 1. ARRANGE: Modify session-specific key
    mock_config_dict["target_model"] = "claude-3-opus"

    # 2. ACT: Use atomic helper
    config_repo.save_config(mock_config_dict)
    loaded_cfg = config_repo.load_config()

    # 3. ASSERT: Verify value was persisted into the state
    assert loaded_cfg["target_model"] == "claude-3-opus"