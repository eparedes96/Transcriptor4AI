# ==============================================================================
# TEST GROUP: FEEDBACK SUBMISSION WORKFLOW (FIXED & SYNCHRONIZED)
# ==============================================================================


import customtkinter as ctk
import pytest

from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window
from transcriptor4ai.shared import constants as const


@pytest.fixture
def mock_gui_env(mocker):
    """
    Initializes a virtualized GUI context with a real hidden root and
    synchronous event scheduling to allow immediate UI assertions.
    """
    # 1. ARRANGE: Create real Tkinter context to support fonts
    app = ctk.CTk()
    app.withdraw()

    mocker.patch.object(app, "after", side_effect=lambda delay, func: func())

    # Mocking system message boxes
    m_info = mocker.patch("tkinter.messagebox.showinfo")
    m_warn = mocker.patch("tkinter.messagebox.showwarning")
    m_error = mocker.patch("tkinter.messagebox.showerror")

    # Mocking diagnostic logs retrieval
    mocker.patch(
        "transcriptor4ai.interface.gui.dialogs.feedback_modal.get_recent_logs",
        return_value="full_system_logs_mock"
    )

    yield {
        "app": app,
        "info": m_info,
        "warn": m_warn,
        "error": m_error
    }

    # CLEANUP: Ensure resources are released
    app.destroy()


@pytest.mark.gui
def test_should_show_warning_when_fields_are_empty(mocker, mock_gui_env):
    """
    Ensures that validation prevents submission if mandatory fields are missing.
    """
    # 1. ARRANGE: Open the modal
    app = mock_gui_env["app"]
    show_feedback_window(app)

    # Identify the top-level window and its buttons
    toplevel = [c for c in app.winfo_children() if isinstance(c, ctk.CTkToplevel)][0]
    send_btn = None
    for widget in toplevel.winfo_children():
        if isinstance(widget, ctk.CTkFrame):
            for sub in widget.winfo_children():
                if isinstance(sub, ctk.CTkButton) and "Send" in sub.cget("text"):
                    send_btn = sub

    # 2. ACT: Click send without filling data
    send_btn._command()

    # 3. ASSERT: Warning was shown
    mock_gui_env["warn"].assert_called_once()
    assert "Subject and Message" in mock_gui_env["warn"].call_args[0][1]


@pytest.mark.gui
def test_should_submit_feedback_successfully(mocker, mock_gui_env):
    """
    Happy Path: Validating that the callback triggers 'showinfo' successfully.
    """
    # 1. ARRANGE: Mock threading and provide valid user input
    app = mock_gui_env["app"]
    m_thread = mocker.patch("threading.Thread")

    # Simulate valid form input
    mocker.patch("customtkinter.CTkEntry.get", return_value="UI Improvement")
    mocker.patch("customtkinter.CTkTextbox.get", return_value="Add more colors.")

    show_feedback_window(app)
    toplevel = [c for c in app.winfo_children() if isinstance(c, ctk.CTkToplevel)][0]

    # Locate Send Button
    send_btn = None
    for widget in toplevel.winfo_children():
        if isinstance(widget, ctk.CTkFrame):
            for sub in widget.winfo_children():
                if isinstance(sub, ctk.CTkButton) and "Send" in sub.cget("text"):
                    send_btn = sub

    # 2. ACT: Trigger Send
    send_btn._command()

    # 3. ASSERT: Extract arguments from the generic telemetry task call
    # thread args: (client, payload, is_error_report, on_complete)
    assert m_thread.called
    thread_args = m_thread.call_args.kwargs["args"]

    payload = thread_args[1]
    is_error = thread_args[2]
    callback = thread_args[3]

    assert payload["subject"] == "UI Improvement"
    assert is_error is False
    assert payload["version"] == const.CURRENT_CONFIG_VERSION

    # Execute callback. Because 'app.after' is patched to be sync,
    # showinfo is called within this same line.
    callback((True, "Success"))

    mock_gui_env["info"].assert_called_once()
    assert "feedback has been sent" in mock_gui_env["info"].call_args[0][1]


@pytest.mark.gui
def test_should_handle_telemetry_failure_gracefully(mocker, mock_gui_env):
    """
    Sad Path: Validating that network failures trigger 'showerror'.
    """
    # 1. ARRANGE
    app = mock_gui_env["app"]
    m_thread = mocker.patch("threading.Thread")
    mocker.patch("customtkinter.CTkEntry.get", return_value="Bug Report")
    mocker.patch("customtkinter.CTkTextbox.get", return_value="Something is broken.")

    show_feedback_window(app)
    toplevel = [c for c in app.winfo_children() if isinstance(c, ctk.CTkToplevel)][0]

    send_btn = None
    for widget in toplevel.winfo_children():
        if isinstance(widget, ctk.CTkFrame):
            for sub in widget.winfo_children():
                if isinstance(sub, ctk.CTkButton) and "Send" in sub.cget("text"):
                    send_btn = sub

    # 2. ACT: Trigger submission
    send_btn._command()

    # Extract callback from thread args
    callback = m_thread.call_args.kwargs["args"][3]

    # Simulate HTTP failure
    callback((False, "HTTP 500: Server Error"))

    # 3. ASSERT: Verify the UI notified the user of the error
    mock_gui_env["error"].assert_called_once()
    assert "500" in mock_gui_env["error"].call_args[0][1]


@pytest.mark.gui
def test_should_redact_logs_when_user_opts_out(mocker, mock_gui_env):
    """
    Privacy: Verify payload content when logging is disabled by user.
    """
    # 1. ARRANGE
    app = mock_gui_env["app"]
    m_thread = mocker.patch("threading.Thread")
    mocker.patch("customtkinter.CTkEntry.get", return_value="Feedback")
    mocker.patch("customtkinter.CTkTextbox.get", return_value="Msg")
    mocker.patch("customtkinter.CTkCheckBox.get", return_value=False)  # Opt-out

    show_feedback_window(app)
    toplevel = [c for c in app.winfo_children() if isinstance(c, ctk.CTkToplevel)][0]

    send_btn = None
    for widget in toplevel.winfo_children():
        if isinstance(widget, ctk.CTkFrame):
            for sub in widget.winfo_children():
                if isinstance(sub, ctk.CTkButton) and "Send" in sub.cget("text"):
                    send_btn = sub

    # 2. ACT
    send_btn._command()

    # 3. ASSERT: Inspect the payload in thread args index 1
    payload = m_thread.call_args.kwargs["args"][1]
    assert "User opted out" in payload["logs"]
    assert "full_system_logs_mock" not in payload["logs"]