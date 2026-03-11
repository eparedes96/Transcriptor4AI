# ==============================================================================
# TEST GROUP: GUI UI HELPERS & WIDGETS
# ==============================================================================

from unittest.mock import MagicMock

import pytest

from transcriptor4ai.interface.gui.common.ui_widgets import (
    CTkScrollableDropdown,
    parse_list_from_string,
)

# ==============================================================================
# TESTS FOR: parse_list_from_string
# ==============================================================================

@pytest.mark.parametrize("input_str, expected_output", [
    (".py, .js, .ts", [".py", ".js", ".ts"]),
    ("  .py , , .js  ", [".py", ".js"]),
    ("", []),
    (None, []),
    ("only_one", ["only_one"]),
])
def test_parse_list_from_string_should_return_sanitized_list(input_str, expected_output):
    """
    Verifies that CSV strings from UI entries are correctly split,
    trimmed, and filtered of empty values.
    """
    # 1. ARRANGE & 2. ACT
    result = parse_list_from_string(input_str)

    # 3. ASSERT
    assert result == expected_output


# ==============================================================================
# TESTS FOR: CTkScrollableDropdown
# ==============================================================================

@pytest.fixture
def mock_ctk_environment(mocker):
    """
    Mocks the customtkinter library components to prevent actual
    window rendering and satisfy attribute lookups during tests.
    """
    # Create the structured ThemeManager mock
    mock_theme_manager = mocker.Mock()
    mock_theme_manager.theme = {
        "CTkFrame": {"fg_color": "gray", "border_color": "black"}
    }
    mocker.patch("customtkinter.ThemeManager", mock_theme_manager)

    # 100% Headless Tkinter Isolation
    mocker.patch("customtkinter.CTkToplevel.__init__", return_value=None)
    mocker.patch("customtkinter.CTkToplevel.withdraw")
    mocker.patch("customtkinter.CTkToplevel.overrideredirect")
    mocker.patch("customtkinter.CTkToplevel.attributes")
    mocker.patch("customtkinter.CTkToplevel.bind")
    mocker.patch("customtkinter.CTkToplevel.after")
    mocker.patch("customtkinter.CTkToplevel.focus_set")
    mocker.patch("customtkinter.CTkToplevel.deiconify")
    mocker.patch("customtkinter.CTkToplevel.geometry")
    mocker.patch("customtkinter.CTkToplevel.destroy")
    mocker.patch("customtkinter.CTkToplevel.winfo_exists", return_value=True)
    mocker.patch("customtkinter.CTkToplevel.focus_get")

    # Mock visual components instantiated inside the dropdown
    mocker.patch("customtkinter.CTkFrame")
    mocker.patch("customtkinter.CTkScrollableFrame")
    mocker.patch("customtkinter.CTkButton")
    mocker.patch("customtkinter.CTkFont")


@pytest.mark.unit
def test_dropdown_initialization_should_setup_ui_structure(mock_ctk_environment):
    """
    Ensures that creating a dropdown instantiates the expected
    container hierarchy and retrieves theme attributes.
    """
    # 1. ARRANGE
    mock_attach = MagicMock()
    mock_attach.winfo_width.return_value = 200

    # 2. ACT
    dropdown = CTkScrollableDropdown(
        attach=mock_attach,
        values=["Model A", "Model B"],
        width=200
    )

    # 3. ASSERT
    assert dropdown._values == ["Model A", "Model B"]
    assert dropdown._width == 200
    assert dropdown.overrideredirect.called


@pytest.mark.unit
def test_dropdown_item_click_should_trigger_command_and_close(mock_ctk_environment):
    """
    Validates that clicking an entry in the dropdown executes
    the logic provided by the controller and cleans up the UI.
    """
    # 1. ARRANGE
    mock_command = MagicMock()
    mock_attach = MagicMock()

    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["Test"], command=mock_command)

    # Reset mock since it might have been called in initialization
    dropdown.destroy.reset_mock()

    # 2. ACT
    dropdown._on_item_click("Selected Value")

    # 3. ASSERT
    mock_command.assert_called_once_with("Selected Value")
    dropdown.destroy.assert_called_once()


@pytest.mark.unit
def test_safe_destroy_should_only_close_if_focus_is_lost(mock_ctk_environment):
    """
    Verifies that the dropdown doesn't close if the focus remains
    within its own window (prevents premature closing during scrolling).
    """
    # 1. ARRANGE
    mock_attach = MagicMock()
    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["A"])

    # FIX: Inject the missing internal Tkinter identifier bypassed by headless mocking
    # This prevents the native __str__ method from throwing an AttributeError
    dropdown._w = ".mock_dropdown_window"

    dropdown.destroy.reset_mock()
    dropdown.winfo_exists.return_value = True

    # Case A: Focus is on a child widget or the dropdown itself
    # Logic: focused_widget.startswith(self) -> ".mock_dropdown_window.child".startswith(".mock_dropdown_window")
    dropdown.focus_get.return_value = MagicMock(__str__=lambda s: ".mock_dropdown_window.child")

    # 2. ACT
    dropdown._safe_destroy()

    # 3. ASSERT
    dropdown.destroy.assert_not_called()

    # Case B: Focus is clearly outside (another window)
    dropdown.focus_get.return_value = MagicMock(__str__=lambda s: ".main_window_entry")

    # 2. ACT
    dropdown._safe_destroy()

    # 3. ASSERT
    dropdown.destroy.assert_called_once()


@pytest.mark.unit
def test_on_focus_out_should_schedule_safe_destruction(mock_ctk_environment):
    """
    Checks that losing focus triggers a delayed destruction
    to allow time for item selection events to process.
    """
    # 1. ARRANGE
    mock_attach = MagicMock()
    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["A"])

    # Reset after mock to ignore the scheduled calls made during __init__
    dropdown.after.reset_mock()

    # 2. ACT
    dropdown._on_focus_out()

    # 3. ASSERT
    dropdown.after.assert_called_once_with(150, dropdown._safe_destroy)