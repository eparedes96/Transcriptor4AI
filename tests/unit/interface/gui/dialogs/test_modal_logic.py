# ==============================================================================
# TEST GROUP: GUI MODAL LOGIC (RESULTS, FEEDBACK, UPDATE, CRASH)
# ==============================================================================

from unittest.mock import MagicMock, patch

import pytest

# ==============================================================================
# FIXTURES: UI ISOLATION
# ==============================================================================

@pytest.fixture(autouse=True)
def mock_ui_libs(mocker):
    """
    Prevents Tcl/Tk errors by mocking all CustomTkinter components globally
    for this module.
    """
    mocker.patch("customtkinter.CTkToplevel", MagicMock())
    mocker.patch("customtkinter.CTkLabel", MagicMock())
    # Note: CTkButton is patched locally in tests to intercept commands
    mocker.patch("customtkinter.CTkButton", MagicMock())
    mocker.patch("customtkinter.CTkTextbox", MagicMock())
    mocker.patch("customtkinter.CTkEntry", MagicMock())
    mocker.patch("customtkinter.CTkFrame", MagicMock())
    mocker.patch("customtkinter.CTkCheckBox", MagicMock())
    mocker.patch("customtkinter.CTkComboBox", MagicMock())
    mocker.patch("customtkinter.CTkScrollableFrame", MagicMock())
    mocker.patch("customtkinter.CTkFont", MagicMock())


from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.interface.gui.dialogs import (
    crash_modal,
    feedback_modal,
    results_modal,
    update_modal,
)


@pytest.fixture
def mock_parent(mocker):
    """Simulates the root application window with clipboard support."""
    parent = mocker.Mock()
    parent.clipboard_clear = MagicMock()
    parent.clipboard_append = MagicMock()
    # Required for update_modal's wait_window
    parent.wait_window = MagicMock()
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
    mock_res.token_count = 1250  # Fix: Must be int for format string :,
    mock_res.summary = {"processed": 5, "skipped": 0, "generated_files": {}}

    mock_explorer = mocker.patch("transcriptor4ai.interface.gui.dialogs.results_modal.open_file_explorer")

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        # Mock constructor must return a mock object to allow .pack()
        MockBtn.return_value = MagicMock()
        results_modal.show_results_window(mock_parent, mock_res)

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
    mock_res.token_count = 5000
    mock_res.summary = {"generated_files": {"unified": "/tmp/full.txt"}}

    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="CONSOLIDATED_CONTENT"))

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        MockBtn.return_value = MagicMock()
        results_modal.show_results_window(mock_parent, mock_res)

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

    # Fix: Ensure .get() returns empty strings, not Mocks (which are truthy)
    mocker.patch("customtkinter.CTkEntry").return_value.get.return_value = "   "
    mocker.patch("customtkinter.CTkTextbox").return_value.get.return_value = "\n"

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        MockBtn.return_value = MagicMock()
        feedback_modal.show_feedback_window(mock_parent)

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
    mock_parent.wait_window = MagicMock()

    # 2. ACT
    with patch("customtkinter.CTkButton") as MockBtn:
        # Fix: side_effect must return a Mock object so .pack() doesn't fail on None
        def side_effect(*args, **kwargs):
            if "Update Now" in kwargs.get("text", ""):
                kwargs["command"]()
            return MagicMock()

        MockBtn.side_effect = side_effect

        result = update_modal.show_update_prompt_modal(
            mock_parent, "3.0.0", "New features", "http://api.com/bin", "/tmp/path"
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
        MockBtn.return_value = MagicMock()
        crash_modal.show_crash_modal("Fatal Error", "Traceback info...", mock_parent)

        for call in MockBtn.call_args_list:
            if "Close Application" in str(call):
                call.kwargs["command"]()

    # 3. ASSERT
    mock_exit.assert_called_once_with(1)