# ==============================================================================
# TEST GROUP: PROFILE LIFECYCLE WORKFLOW (SAVE, LOAD, DELETE)
# ==============================================================================

import pytest
import os
from unittest.mock import MagicMock, patch
from transcriptor4ai.interface.gui.controllers.profile_controller import ProfileController


@pytest.fixture
def profile_env(mocker, mock_config_dict):
    """
    Sets up a fully mocked environment for Profile Controller testing,
    simulating the AppController (Mediator) and its dependencies.
    """
    # 1. ARRANGE: Prepare mocks
    coordinator = mocker.Mock()
    coordinator.app = mocker.Mock()
    coordinator.config = mock_config_dict.copy()

    # Simulate an app_state with one existing profile
    coordinator.app_state = {
        "saved_profiles": {
            "Legacy Profile": {"minify_output": True, "processing_depth": "tree_only"}
        }
    }

    # Mock views
    settings_view = mocker.Mock()
    coordinator.settings_view = settings_view

    # Mock infrastructure
    mock_repo = mocker.Mock()
    coordinator.get_config_repo.return_value = mock_repo

    controller = ProfileController(coordinator)

    return {
        "controller": controller,
        "coordinator": coordinator,
        "repo": mock_repo,
        "view": settings_view
    }


@pytest.mark.gui
def test_should_save_new_profile_and_persist_data(mocker, profile_env):
    """
    Ensures that providing a unique name saves the current state into the
    repository and updates the UI list.
    """
    env = profile_env

    # 1. ARRANGE: Mock user entering a new profile name
    mocker.patch("customtkinter.CTkInputDialog.get_input", return_value="New Shiny Profile")
    m_info = mocker.patch("tkinter.messagebox.showinfo")

    # 2. ACT: Execute Save
    env["controller"].save_profile()

    # 3. ASSERT: Verification
    # Ensure current config was copied into the state
    assert "New Shiny Profile" in env["coordinator"].app_state["saved_profiles"]
    assert env["coordinator"].app_state["saved_profiles"]["New Shiny Profile"] == env["coordinator"].config

    # Ensure physical persistence was triggered
    env["repo"].save_app_state.assert_called_once_with(env["coordinator"].app_state)

    # Ensure UI ComboBox was updated with the new list
    env["view"].combo_profiles.configure.assert_called()
    env["view"].combo_profiles.set.assert_called_with("New Shiny Profile")


@pytest.mark.gui
def test_should_ask_confirmation_when_overwriting_existing_profile(mocker, profile_env):
    """
    Validates that the system identifies duplicate profile names and
    prompts the user before replacing data.
    """
    env = profile_env

    # 1. ARRANGE: Simulate entering an existing name
    mocker.patch("customtkinter.CTkInputDialog.get_input", return_value="Legacy Profile")
    # Mock user clicks "No" on overwrite confirmation
    m_ask = mocker.patch("tkinter.messagebox.askyesno", return_value=False)

    # 2. ACT
    env["controller"].save_profile()

    # 3. ASSERT
    m_ask.assert_called_once()
    # Repository should NOT be called since user cancelled
    env["repo"].save_app_state.assert_not_called()


@pytest.mark.gui
def test_should_load_profile_and_sync_views(mocker, profile_env):
    """
    Verifies that selecting a profile updates the internal config object
    and triggers a UI synchronization cycle.
    """
    env = profile_env

    # 1. ARRANGE: Select the profile in the mock ComboBox
    env["view"].combo_profiles.get.return_value = "Legacy Profile"
    m_info = mocker.patch("tkinter.messagebox.showinfo")

    # Ensure we mock the domain default getter used for merging
    mocker.patch("transcriptor4ai.domain.entities.app_config.get_default_config", return_value={})

    # 2. ACT
    env["controller"].load_profile()

    # 3. ASSERT: Logic check
    # The processing_depth from Legacy Profile should now be in the active config
    assert env["coordinator"].config["processing_depth"] == "tree_only"

    # Ensure the view synchronization was triggered via the coordinator
    env["coordinator"].sync_view_from_config.assert_called_once()
    m_info.assert_called_once()


@pytest.mark.gui
def test_should_delete_profile_after_confirmation(mocker, profile_env):
    """
    Ensures profile removal is permanent and requires explicit user consent.
    """
    env = profile_env

    # 1. ARRANGE
    env["view"].combo_profiles.get.return_value = "Legacy Profile"
    m_ask = mocker.patch("tkinter.messagebox.askyesno", return_value=True)

    # 2. ACT
    env["controller"].delete_profile()

    # 3. ASSERT
    assert "Legacy Profile" not in env["coordinator"].app_state["saved_profiles"]
    env["repo"].save_app_state.assert_called_once()

    # Verify the ComboBox list was refreshed
    env["view"].combo_profiles.configure.assert_called()
    # Should reset selection to "-- No Profile --"
    assert env["view"].combo_profiles.set.call_args[0][0] != "Legacy Profile"


@pytest.mark.gui
def test_should_ignore_actions_when_no_profile_is_selected(mocker, profile_env):
    """
    Edge Case: Loading or Deleting when no profile is selected should be a no-op.
    """
    env = profile_env

    # 1. ARRANGE: ComboBox is empty or on default label
    env["view"].combo_profiles.get.return_value = "-- No Profile --"
    m_ask = mocker.patch("tkinter.messagebox.askyesno")

    # 2. ACT
    env["controller"].load_profile()
    env["controller"].delete_profile()

    # 3. ASSERT: No side effects occurred
    m_ask.assert_not_called()
    env["repo"].save_app_state.assert_not_called()
    env["coordinator"].sync_view_from_config.assert_not_called()