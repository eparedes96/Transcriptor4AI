# ==============================================================================
# TEST GROUP: TRANSCRIPTION EXECUTION WORKFLOW (FIXED)
# ==============================================================================

import pytest
import threading
from unittest.mock import MagicMock, patch, ANY
from transcriptor4ai.interface.gui.controllers.execution_controller import ExecutionController
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult


@pytest.fixture
def execution_env(mocker, mock_config_dict):
    """
    Sets up a fully mocked environment for Execution Controller testing.
    Mocks the coordinator and UI components to avoid real Tkinter side effects.
    """
    # 1. ARRANGE: Prepare Coordinator and App mocks
    coordinator = mocker.Mock()
    coordinator.app = mocker.Mock()

    # Simulate 'app.after' to execute callbacks immediately
    coordinator.app.after.side_effect = lambda delay, fn: fn()

    coordinator.config = mock_config_dict.copy()
    coordinator.config["input_path"] = "/valid/path"

    # Mock Dashboard View and UI elements
    dash = mocker.Mock()
    coordinator.dashboard_view = dash

    # Mock Services and Ports
    coordinator.get_filesystem.return_value = mocker.Mock()
    coordinator.get_cache.return_value = mocker.Mock()
    coordinator.get_user_context.return_value = mocker.Mock()
    coordinator.cost_estimator = mocker.Mock()

    controller = ExecutionController(coordinator)

    return {
        "controller": controller,
        "coordinator": coordinator,
        "dash": dash,
        "fs": coordinator.get_filesystem.return_value
    }


@pytest.mark.gui
def test_should_start_pipeline_and_show_results_on_success(mocker, execution_env):
    """
    Happy Path: Valid execution updates cost display and shows the results modal.
    """
    env = execution_env

    # 1. ARRANGE: Set success preconditions
    env["fs"].directory_exists.return_value = True

    # Mock result from the transcription engine
    success_res = MagicMock(spec=PipelineResult)
    success_res.ok = True
    success_res.token_count = 5000

    # Patch Threading and results modal
    m_thread = mocker.patch("threading.Thread")
    m_results_modal = mocker.patch("transcriptor4ai.interface.gui.dialogs.results_modal.show_results_window")

    env["coordinator"].cost_estimator.calculate_cost.return_value = 0.05
    env["coordinator"].cost_estimator.get_context_window.return_value = 128000

    # 2. ACT: Start pipeline execution
    env["controller"].run_pipeline(dry_run=False)

    # Simulate thread completion by manually calling the captured callback
    # callback is at index 6 of the 'args' tuple passed to the thread
    thread_args = m_thread.call_args.kwargs["args"]
    callback = thread_args[6]
    callback(success_res)

    # 3. ASSERT: Verify UI and financial updates
    env["dash"].btn_process.configure.assert_any_call(state="disabled")

    # Verify cost logic was applied
    env["coordinator"].cost_estimator.calculate_cost.assert_called_with(5000, ANY)
    env["dash"].update_cost_display.assert_called_with(0.05)

    # Verify results modal was triggered
    m_results_modal.assert_called_once_with(env["coordinator"].app, success_res)


@pytest.mark.gui
def test_should_abort_execution_when_input_path_is_invalid(mocker, execution_env):
    """
    Sad Path: Execution should be blocked if the source directory is missing.
    """
    env = execution_env

    # 1. ARRANGE: Non-existent path
    env["fs"].directory_exists.return_value = False
    m_error = mocker.patch("tkinter.messagebox.showerror")
    m_thread = mocker.patch("threading.Thread")

    # 2. ACT: Try to run
    env["controller"].run_pipeline()

    # 3. ASSERT: Thread should not start, user notified via error box
    m_error.assert_called_once()
    m_thread.assert_not_called()


@pytest.mark.gui
def test_should_warn_user_on_context_window_overflow(mocker, execution_env):
    """
    Edge Case: The transcription succeeds but the project is too large for the model.
    """
    env = execution_env

    # 1. ARRANGE: Success result with huge token count
    env["fs"].directory_exists.return_value = True
    success_res = MagicMock(spec=PipelineResult)
    success_res.ok = True
    success_res.token_count = 200000

    m_thread = mocker.patch("threading.Thread")
    m_warn = mocker.patch("tkinter.messagebox.showwarning")
    mocker.patch("transcriptor4ai.interface.gui.dialogs.results_modal.show_results_window")

    # Set limit below the token count
    env["coordinator"].cost_estimator.get_context_window.return_value = 128000

    # 2. ACT
    env["controller"].run_pipeline()
    # Execute callback from thread kwargs
    callback = m_thread.call_args.kwargs["args"][6]
    callback(success_res)

    # 3. ASSERT: Warning message should be triggered
    m_warn.assert_called_once()
    assert "exceed" in m_warn.call_args[0][1]


@pytest.mark.gui
def test_should_handle_pipeline_cancellation_state(mocker, execution_env):
    """
    Behavior: Aborting the pipeline must signal the thread event and update UI.
    """
    env = execution_env

    # 1. ARRANGE: Reset event
    env["controller"]._cancellation_event.clear()

    # 2. ACT: User aborts
    env["controller"].abort_pipeline()

    # 3. ASSERT: Event is set and button reflects state
    assert env["controller"]._cancellation_event.is_set()
    env["dash"].btn_process.configure.assert_called_with(
        text="CANCELING...",
        state="disabled"
    )


@pytest.mark.gui
def test_should_show_crash_modal_on_unhandled_exception(mocker, execution_env):
    """
    Sad Path: If the background task throws an Exception, the Crash Modal must open.
    """
    env = execution_env

    # 1. ARRANGE: Exception object to simulate thread crash
    env["fs"].directory_exists.return_value = True
    fatal_error = RuntimeError("Thread panic - disk failure")

    m_thread = mocker.patch("threading.Thread")
    m_crash_modal = mocker.patch("transcriptor4ai.interface.gui.dialogs.crash_modal.show_crash_modal")

    # 2. ACT
    env["controller"].run_pipeline()
    # Pass exception to callback
    callback = m_thread.call_args.kwargs["args"][6]
    callback(fatal_error)

    # 3. ASSERT: Standard crash reporting tool should be displayed
    m_crash_modal.assert_called_once_with(
        str(fatal_error),
        ANY,
        env["coordinator"].app
    )