from __future__ import annotations

from unittest.mock import ANY, patch

# ==============================================================================
# TEST GROUP: EXECUTION CONTROLLER (GUI LOGIC)
# ==============================================================================
import pytest

from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.interface.gui.controllers.execution_controller import ExecutionController


@pytest.fixture
def mock_main(mocker, mock_config_dict):
    """
    Creates a full mock of the AppController coordinator.
    Simulates the main hub that connects Infrastructure, UI, and Business Logic.
    """
    coordinator = mocker.Mock()
    coordinator.config = mock_config_dict
    coordinator.app = mocker.Mock()

    # Critical: Ensure app.after executes the callback immediately
    # to simulate the UI loop processing the thread result synchronously.
    coordinator.app.after.side_effect = lambda delay, fn: fn()

    # Mock views
    coordinator.dashboard_view = mocker.Mock()

    # Mock Services
    coordinator.get_filesystem.return_value = mocker.Mock()
    coordinator.get_cache.return_value = mocker.Mock()
    coordinator.get_user_context.return_value = mocker.Mock()
    coordinator.cost_estimator = mocker.Mock()

    return coordinator


@pytest.fixture
def controller(mock_main):
    """Returns an instance of the SUT with the mock coordinator."""
    return ExecutionController(mock_main)


@pytest.mark.unit
def test_run_pipeline_aborts_if_input_dir_missing(controller, mock_main, mocker):
    """
    Ensures that execution is blocked and an error is shown if the
    input path is invalid.
    """
    # 1. ARRANGE: Filesystem reports directory missing
    mock_main.get_filesystem().directory_exists.return_value = False
    mock_mb = mocker.patch("transcriptor4ai.interface.gui.controllers.execution_controller.mb.showerror")

    # 2. ACT
    controller.run_pipeline()

    # 3. ASSERT: Error popup shown, button NOT updated (process blocked)
    mock_mb.assert_called_once()
    assert mock_main.dashboard_view.btn_process.configure.call_count == 0


@pytest.mark.unit
@patch("threading.Thread")
def test_run_pipeline_starts_background_thread(mock_thread_cls, controller, mock_main):
    """
    Verifies that the controller correctly triggers a daemon thread
    for the pipeline task and resets cancellation state.
    """
    # 1. ARRANGE
    mock_main.get_filesystem().directory_exists.return_value = True

    # Simulate a "dirty" state where a previous run was cancelled
    controller._cancellation_event.set()

    # 2. ACT
    controller.run_pipeline(dry_run=True)

    # 3. ASSERT
    # Verify UI visual feedback
    mock_main.dashboard_view.btn_process.configure.assert_any_call(
        text=ANY, fg_color="gray"
    )

    # Verify Cancellation Event was RESET (Critical for restartability)
    assert not controller._cancellation_event.is_set()

    # Verify thread creation
    mock_thread_cls.assert_called_once()
    assert mock_thread_cls.call_args[1]["daemon"] is True


@pytest.mark.unit
def test_process_result_handles_overwrite_decision(controller, mock_main, mocker):
    """
    Scenario: Pipeline fails due to existing files.
    The controller must ask the user and restart with overwrite=True if accepted.
    """
    # 1. ARRANGE
    collision_result = mocker.Mock(spec=PipelineResult)
    collision_result.ok = False
    collision_result.existing_files = ["file1.txt"]

    # Mock user clicking "Yes" on overwrite prompt
    mock_ask = mocker.patch("transcriptor4ai.interface.gui.controllers.execution_controller.mb.askyesno",
                            return_value=True)

    # Mock recursive call to run_pipeline to avoid actual thread start
    mocker.patch.object(controller, "run_pipeline")

    # 2. ACT
    controller.process_result_and_modals(collision_result)

    # 3. ASSERT
    mock_ask.assert_called_once()
    # Ensure recursive call passes the overwrite flag
    controller.run_pipeline.assert_called_with(dry_run=False, overwrite=True)


@pytest.mark.unit
def test_process_result_alerts_on_context_overflow(controller, mock_main, mocker):
    """
    Ensures a warning is shown if the generated token count exceeds
    the model's context window.
    """
    # 1. ARRANGE
    success_result = mocker.Mock(spec=PipelineResult)
    success_result.ok = True
    success_result.token_count = 150000  # Higher than limit

    mock_main.cost_estimator.get_context_window.return_value = 128000
    mock_warn = mocker.patch("transcriptor4ai.interface.gui.controllers.execution_controller.mb.showwarning")
    mocker.patch("transcriptor4ai.interface.gui.controllers.execution_controller.results_modal.show_results_window")

    # 2. ACT
    controller.process_result_and_modals(success_result)

    # 3. ASSERT
    mock_warn.assert_called_once_with("Context Overflow", ANY)


@pytest.mark.unit
def test_process_result_shows_crash_modal_on_exception(controller, mock_main, mocker):
    """
    Verifies that any unhandled exception in the background thread
    is routed to the custom crash modal.
    """
    # 1. ARRANGE
    error_obj = RuntimeError("Fatal Pipeline Crash")
    mock_crash = mocker.patch(
        "transcriptor4ai.interface.gui.controllers.execution_controller.crash_modal.show_crash_modal")

    # 2. ACT
    controller.process_result_and_modals(error_obj)

    # 3. ASSERT
    mock_crash.assert_called_once_with(str(error_obj), ANY, mock_main.app)


@pytest.mark.unit
def test_abort_pipeline_signals_cancel_event(controller, mock_main):
    """
    Verifies that clicking 'Cancel' correctly sets the threading.Event
    and updates the UI button.
    """
    # 1. ARRANGE: Cancellation event is false by default
    assert controller._cancellation_event.is_set() is False

    # 2. ACT
    controller.abort_pipeline()

    # 3. ASSERT
    assert controller._cancellation_event.is_set() is True

    # Button should indicate canceling state
    mock_main.dashboard_view.btn_process.configure.assert_called_with(
        text="CANCELING...", state="disabled"
    )