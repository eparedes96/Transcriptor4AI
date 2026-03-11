# ==============================================================================
# TEST GROUP: GUI UPDATE CONTROLLER
# ==============================================================================

from unittest.mock import ANY

import pytest

from transcriptor4ai.application.services.update_service import UpdateStatus
from transcriptor4ai.interface.gui.controllers.update_controller import UpdateController


@pytest.fixture
def update_env(mocker):
    """
    Sets up a fully mocked environment for Update Controller testing.
    Mocks the UI thread marshalling and view components.
    """
    mock_app = mocker.Mock()
    # Simulate immediate execution of the 'after' callback for testing
    mock_app.after.side_effect = lambda delay, func: func()

    mock_sidebar = mocker.Mock()
    # Mock the update badge button
    mock_sidebar.update_badge = mocker.Mock()

    mock_manager = mocker.Mock()
    mock_manager.update_info = {}
    mock_manager.status = UpdateStatus.IDLE

    controller = UpdateController(mock_app, mock_sidebar, mock_manager)

    return {
        "controller": controller,
        "app": mock_app,
        "sidebar": mock_sidebar,
        "manager": mock_manager
    }


# ==============================================================================
# PROCESS: BACKGROUND CYCLE INITIATION
# ==============================================================================

@pytest.mark.unit
def test_run_silent_cycle_should_trigger_manager_and_schedule_callback(mocker, update_env):
    """
    Verifies that the silent check calls the manager and correctly
    marshals the result back to the UI thread.
    """
    # 1. ARRANGE
    env = update_env
    env["manager"].update_info = {"has_update": True, "latest_version": "3.0.0"}

    # 2. ACT
    env["controller"].run_silent_cycle(manual=False)

    # 3. ASSERT
    # Check if logic service was called
    env["manager"].run_silent_cycle.assert_called_once()
    # Check if UI was notified via 'after' (simulated by side_effect)
    env["sidebar"].update_badge.configure.assert_called()


# ==============================================================================
# PROCESS: UI STATE UPDATES (ON UPDATE CHECKED)
# ==============================================================================

@pytest.mark.unit
def test_on_update_checked_should_enable_sidebar_badge_when_update_exists(update_env):
    """
    Ensures the sidebar update notification becomes active and visible
    when a new version is detected.
    """
    # 1. ARRANGE
    env = update_env
    update_data = {
        "has_update": True,
        "latest_version": "2.2.0",
        "changelog": "Bug fixes",
        "binary_url": "http://api.com/v2.2.0.exe"
    }

    # 2. ACT
    env["controller"]._on_update_checked(update_data, is_manual=False)

    # 3. ASSERT
    # Badge should show the new version number
    env["sidebar"].update_badge.configure.assert_any_call(
        text="Update v2.2.0",
        state="normal",
        command=ANY
    )
    # Badge must be placed in the sidebar grid
    env["sidebar"].update_badge.grid.assert_called_once()


@pytest.mark.unit
def test_on_update_checked_should_show_info_if_manual_and_no_update(mocker, update_env):
    """
    Verifies that if a user manually checks for updates and none are found,
    a confirmation message is displayed.
    """
    # 1. ARRANGE
    env = update_env
    mock_mb = mocker.patch("tkinter.messagebox.showinfo")
    update_data = {"has_update": False}

    # 2. ACT
    env["controller"]._on_update_checked(update_data, is_manual=True)

    # 3. ASSERT
    mock_mb.assert_called_once_with("Update Check", ANY)
    env["sidebar"].update_badge.grid.assert_not_called()


@pytest.mark.unit
def test_on_update_checked_should_trigger_prompt_immediately_on_manual_discovery(mocker, update_env):
    """
    Behavioral Test: If the check was manual, the controller should show the
    detailed prompt modal immediately, not just the badge.
    """
    # 1. ARRANGE
    env = update_env
    mock_prompt = mocker.patch("transcriptor4ai.interface.gui.controllers.update_controller.show_update_prompt_modal")
    update_data = {
        "has_update": True,
        "latest_version": "3.0.1",
        "pending_path": "/tmp/staged_update.exe"
    }

    # 2. ACT
    env["controller"]._on_update_checked(update_data, is_manual=True)

    # 3. ASSERT
    mock_prompt.assert_called_once_with(
        env["app"], "3.0.1", ANY, ANY, "/tmp/staged_update.exe", ANY
    )


# ==============================================================================
# PROCESS: BADGE COMMAND BINDING
# ==============================================================================

@pytest.mark.unit
def test_badge_command_should_open_update_modal(mocker, update_env):
    """
    Validates that the command assigned to the sidebar badge correctly
    invokes the modal display logic with full context.
    """
    # 1. ARRANGE
    env = update_env
    mock_prompt = mocker.patch("transcriptor4ai.interface.gui.controllers.update_controller.show_update_prompt_modal")
    update_data = {
        "has_update": True,
        "latest_version": "2.5.0",
        "changelog": "UI Refactor",
        "binary_url": "http://api.com/bin"
    }

    # 2. ACT
    env["controller"]._on_update_checked(update_data, is_manual=False)

    # Extract the command passed to configure and call it
    badge_call_args = env["sidebar"].update_badge.configure.call_args
    badge_command = badge_call_args.kwargs["command"]
    badge_command()

    # 3. ASSERT
    mock_prompt.assert_called_once_with(
        env["app"], "2.5.0", "UI Refactor", "http://api.com/bin", "", ANY
    )