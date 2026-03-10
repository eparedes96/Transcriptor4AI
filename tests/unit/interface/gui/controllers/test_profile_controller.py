# ==============================================================================
# TEST GROUP: GUI PROFILE CONTROLLER LOGIC
# ==============================================================================

import pytest
from unittest.mock import MagicMock, patch
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController


@pytest.fixture
def profile_env(mocker, mock_config_dict):
    """
    Sets up a fully mocked environment for Profile Controller testing.
    Isolates the controller from real UI loop and filesystem.
    """
    coordinator = mocker.Mock()
    coordinator.config = mock_config_dict.copy()
    coordinator.app_state = {
        "saved_profiles": {
            "Legacy Profile": {"minify_output": True, "target_model": "old-gpt"}
        }
    }

    # Mock Views
    settings_view = mocker.Mock()
    coordinator.settings_view = settings_view

    # Mock Repository Port
    mock_repo = mocker.Mock()
    coordinator.get_config_repo.return_value = mock_repo

    controller = ProfileController(coordinator)

    return {
        "controller": controller,
        "coordinator": coordinator,
        "repo": mock_repo,
        "view": settings_view
    }


# ==============================================================================
# TEST GROUP: PROFILE LOADING
# ==============================================================================

@pytest.mark.unit
def test_load_profile_should_merge_data_and_refresh_ui(mocker, profile_env):
    """
    Ensures that loading a profile updates the active session config and
    triggers a view synchronization.
    """
    # 1. ARRANGE: Select a valid profile in the UI
    env = profile_env
    env["view"].combo_profiles.get.return_value = "Legacy Profile"
    m_info = mocker.patch("tkinter.messagebox.showinfo")

    # Mock default config to simulate the merge logic in load_profile
    mocker.patch("transcriptor4ai.domain.entities.app_config.get_default_config",
                 return_value={"extensions": [".py"]})

    # 2. ACT
    env["controller"].load_profile()

    # 3. ASSERT
    # Verify the specific key from the profile was loaded
    assert env["coordinator"].config["target_model"] == "old-gpt"
    # Verify UI synchronization was triggered
    env["coordinator"].sync_view_from_config.assert_called_once()
    m_info.assert_called_once()


@pytest.mark.unit
def test_load_profile_should_ignore_if_no_selection(profile_env):
    """
    Verifies that the controller returns early if no valid profile is selected.
    """
    # 1. ARRANGE
    env = profile_env
    env["view"].combo_profiles.get.return_value = "-- No Profile --"

    # 2. ACT
    env["controller"].load_profile()

    # 3. ASSERT
    env["coordinator"].sync_view_from_config.assert_not_called()


# ==============================================================================
# TEST GROUP: PROFILE SAVING
# ==============================================================================

@pytest.mark.unit
def test_save_profile_should_persist_new_preset(mocker, profile_env):
    """
    Validates the creation of a new profile including repo persistence
    and ComboBox list update.
    """
    # 1. ARRANGE
    env = profile_env
    profile_name = "New Pro Architecture"
    mocker.patch("customtkinter.CTkInputDialog.get_input", return_value=profile_name)
    m_info = mocker.patch("tkinter.messagebox.showinfo")

    # 2. ACT
    env["controller"].save_profile()

    # 3. ASSERT: State, Repo, and UI updated
    assert profile_name in env["coordinator"].app_state["saved_profiles"]
    env["repo"].save_app_state.assert_called_once_with(env["coordinator"].app_state)
    env["view"].combo_profiles.configure.assert_called()  # Check for list refresh
    env["view"].combo_profiles.set.assert_called_with(profile_name)


@pytest.mark.unit
def test_save_profile_should_handle_overwrite_confirmation(mocker, profile_env):
    """
    Checks that existing profiles trigger an overwrite warning and respect
    the user's decision to abort.
    """
    # 1. ARRANGE
    env = profile_env
    mocker.patch("customtkinter.CTkInputDialog.get_input", return_value="Legacy Profile")
    # User says NO to overwrite
    m_ask = mocker.patch("tkinter.messagebox.askyesno", return_value=False)

    # 2. ACT
    env["controller"].save_profile()

    # 3. ASSERT: Operation aborted, repo not called
    m_ask.assert_called_once()
    env["repo"].save_app_state.assert_not_called()


# ==============================================================================
# TEST GROUP: PROFILE DELETION
# ==============================================================================

@pytest.mark.unit
def test_delete_profile_should_remove_data_after_confirmation(mocker, profile_env):
    """
    Ensures permanent removal of a profile from memory and disk after user consent.
    """
    # 1. ARRANGE
    env = profile_env
    env["view"].combo_profiles.get.return_value = "Legacy Profile"
    mocker.patch("tkinter.messagebox.askyesno", return_value=True)

    # 2. ACT
    env["controller"].delete_profile()

    # 3. ASSERT
    assert "Legacy Profile" not in env["coordinator"].app_state["saved_profiles"]
    env["repo"].save_app_state.assert_called_once()
    # Ensure UI resets to "No Profile"
    env["view"].combo_profiles.set.assert_called_with("-- No Profile --")


@pytest.mark.unit
def test_delete_profile_should_abort_if_user_cancels(mocker, profile_env):
    """
    Verifies that state and repository remain unchanged if deletion is rejected.
    """
    # 1. ARRANGE
    env = profile_env
    env["view"].combo_profiles.get.return_value = "Legacy Profile"
    mocker.patch("tkinter.messagebox.askyesno", return_value=False)

    # 2. ACT
    env["controller"].delete_profile()

    # 3. ASSERT
    assert "Legacy Profile" in env["coordinator"].app_state["saved_profiles"]
    env["repo"].save_app_state.assert_not_called()