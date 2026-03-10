# ==============================================================================
# TEST GROUP: GUI MODAL LOGIC (RESULTS, FEEDBACK, UPDATE, CRASH)
# ==============================================================================

import pytest
import os
from unittest.mock import MagicMock, patch, ANY


# Mocking the UI libraries before importing dialogs to avoid Tcl/Tk errors in headless environments
@pytest.fixture(autouse=True)
def mock_ui_libs(mocker):
    mocker.patch("customtkinter.CTkToplevel", MagicMock())
    mocker.patch("customtkinter.CTkLabel", MagicMock())
    mocker.patch("customtkinter.CTkButton", MagicMock())
    mocker.patch("customtkinter.CTkTextbox", MagicMock())
    mocker.patch("customtkinter.CTkEntry", MagicMock())
    mocker.patch("customtkinter.CTkFrame", MagicMock())
    mocker.patch("customtkinter.CTkCheckBox", MagicMock())
    mocker.patch("customtkinter.CTkComboBox", MagicMock())


from transcriptor4ai.interface.gui.dialogs import results_modal, feedback_modal, update_modal, crash_modal
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult


@pytest.fixture
def mock_parent(mocker):
    """Simulates the root application window."""
    parent = mocker.Mock()
    parent.clipboard_clear = MagicMock()
    parent.clipboard_append = MagicMock()
    return parent


# ==============================================================================
# TEST GROUP: RESULTS MODAL LOGIC
# ==============================================================================

@pytest.mark.unit
def test_results_modal_open_folder_should_call_system_explorer(mocker, mock_parent):
    """
    Verifies that the 'Open Folder' button triggers the OS file explorer.
    """
    # 1. ARRANGE
    mock_res = mocker.Mock(spec=PipelineResult)
    mock_res.final_output_path = "/path/to/results"
    mock_res.summary = {"generated_files": {}}

    mock_explorer = mocker.patch("transcriptor4ai.interface.gui.dialogs.results_modal.open_file_explorer")

    # 2. ACT
    # We don't call show_results_window directly to avoid wait_window blocking.
    # Instead, we test the internal handler logic if exported, or mock the button call.
    with patch("customtkinter.CTkButton") as MockBtn:
        results_modal.show_results_window(mock_parent, mock_res)

        # Find the "Open Folder" button by text and trigger its command
        for call in MockBtn.call_args_list:
            if "Open Folder" in str(call):
                call.kwargs["command"]()

    # 3. ASSERT
    mock_explorer.assert_called_once_with("/path/to/results")


@pytest.mark.unit
def test_results_modal_copy_should_read_file_to_clipboard(mocker, mock_parent):
    """
    Validates that copying context reads from disk and populates the clipboard.
    """
    # 1. ARRANGE
    mock_res = mocker.Mock(spec=PipelineResult)
    mock_res.summary = {"generated_files": {"unified": "/tmp/full.txt"}}

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="CONSOLIDATED_CONTENT"))

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        results_modal.show_results_window(mock_parent, mock_res)

        # Trigger the "Copy" command
        for call in MockBtn.call_args_list:
            if "Copy" in str(call):
                call.kwargs["command"]()

    # 3. ASSERT
    mock_parent.clipboard_clear.assert_called_once()
    mock_parent.clipboard_append.assert_called_once_with("CONSOLIDATED_CONTENT")


# ==============================================================================
# TEST GROUP: FEEDBACK MODAL LOGIC
# ==============================================================================

@pytest.mark.unit
def test_feedback_modal_should_validate_required_fields(mocker, mock_parent):
    """
    Ensures that empty subject or message blocks the submission.
    """
    # 1. ARRANGE
    mock_warn = mocker.patch("tkinter.messagebox.showwarning")

    # Mock empty inputs
    mocker.patch("customtkinter.CTkEntry.get", return_value="   ")
    mocker.patch("customtkinter.CTkTextbox.get", return_value="/n")

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        feedback_modal.show_feedback_window(mock_parent)
        # Find "Send Feedback" button
        for call in MockBtn.call_args_list:
            if "Send Feedback" in str(call):
                call.kwargs["command"]()

    # 3. ASSERT
    mock_warn.assert_called_once()
    assert "Subject and Message" in mock_warn.call_args[0][1]


# ==============================================================================
# TEST GROUP: UPDATE MODAL LOGIC
# ==============================================================================

@pytest.mark.unit
def test_update_modal_auto_update_selection_returns_true(mocker, mock_parent):
    """
    Validates that the update prompt correctly returns the user's intent
    to perform an automated update.
    """
    # 1. ARRANGE
    # Since wait_window blocks, we must mock it to return immediately
    mock_parent.wait_window = MagicMock()

    # 2. ACT
    # We use a trick: execute the command of the "Update Now" button via mock
    with patch("customtkinter.CTkButton") as MockBtn:
        # We need to capture the toplevel instance to destroy it and unblock
        # but here we just want to see if the internal list state changes

        # Simulating the button click inside the function execution
        def side_effect(*args, **kwargs):
            if "Update Now" in kwargs.get("text", ""):
                # This is the command that sets update_requested[0] = True
                kwargs["command"]()

        MockBtn.side_effect = side_effect

        result = update_modal.show_update_prompt_modal(
            mock_parent, "3.0.0", "Logs", "url", "path"
        )

    # 3. ASSERT
    assert result is True


# ==============================================================================
# TEST GROUP: CRASH MODAL LOGIC
# ==============================================================================

@pytest.mark.unit
def test_crash_modal_close_should_terminate_process(mocker, mock_parent):
    """
    Critical Test: The crash modal must provide a way to safely exit
    the application after a fatal error.
    """
    # 1. ARRANGE
    mock_exit = mocker.patch("sys.exit")

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        crash_modal.show_crash_modal("Fatal!", "Trace...", mock_parent)

        for call in MockBtn.call_args_list:
            if "Close Application" in str(call):
                call.kwargs["command"]()

    # 3. ASSERT
    mock_exit.assert_called_once_with(1)