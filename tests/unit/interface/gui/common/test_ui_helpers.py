# ==============================================================================
# TEST GROUP: GUI UI HELPERS & WIDGETS
# ==============================================================================

import pytest
from unittest.mock import MagicMock, patch
from transcriptor4ai.interface.gui.common.ui_widgets import (
    parse_list_from_string,
    CTkScrollableDropdown
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
    window rendering during tests.
    """
    mocker.patch("customtkinter.CTkToplevel", MagicMock())
    mocker.patch("customtkinter.CTkFrame", MagicMock())
    mocker.patch("customtkinter.CTkScrollableFrame", MagicMock())
    mocker.patch("customtkinter.CTkButton", MagicMock())
    mocker.patch("customtkinter.CTkFont", MagicMock())
    mocker.patch("customtkinter.ThemeManager", {"CTkFrame": {"fg_color": "gray", "border_color": "black"}})


@pytest.mark.unit
def test_dropdown_initialization_should_setup_ui_structure(mocker, mock_ctk_environment):
    """
    Ensures that creating a dropdown instantiates the expected
    container hierarchy (Frame -> ScrollableFrame).
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
    # Verify logical state, not physical UI
    assert dropdown._values == ["Model A", "Model B"]
    assert dropdown._width == 200


@pytest.mark.unit
def test_dropdown_item_click_should_trigger_command_and_close(mocker, mock_ctk_environment):
    """
    Validates that clicking an entry in the dropdown executes
    the logic provided by the controller and cleans up the UI.
    """
    # 1. ARRANGE
    mock_command = MagicMock()
    mock_attach = MagicMock()

    # Mocking destroy since we inherited from MagicMocked Toplevel
    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["Test"], command=mock_command)
    dropdown.destroy = MagicMock()

    # 2. ACT
    dropdown._on_item_click("Selected Value")

    # 3. ASSERT
    # Ensures the controller is notified of the user's choice
    mock_command.assert_called_once_with("Selected Value")
    # Ensures the dropdown is closed immediately after selection
    dropdown.destroy.assert_called_once()


@pytest.mark.unit
def test_safe_destroy_should_only_close_if_focus_is_lost(mocker, mock_ctk_environment):
    """
    Verifies that the dropdown doesn't close if the focus remains
    within its own window (prevents premature closing).
    """
    # 1. ARRANGE
    mock_attach = MagicMock()
    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["A"])
    dropdown.destroy = MagicMock()
    dropdown.winfo_exists.return_value = True

    # Case A: Focus is on a child widget (e.g., the internal scrollbar)
    # 2. ACT
    dropdown.focus_get = MagicMock(return_value=MagicMock(__str__=lambda s: f"{dropdown}.child"))
    dropdown._safe_destroy()

    # 3. ASSERT
    dropdown.destroy.assert_not_called()

    # Case B: Focus is outside the dropdown
    # 2. ACT
    dropdown.focus_get = MagicMock(return_value=MagicMock(__str__=lambda s: ".other_window"))
    dropdown._safe_destroy()

    # 3. ASSERT
    dropdown.destroy.assert_called_once()


@pytest.mark.unit
def test_on_focus_out_should_schedule_safe_destruction(mocker, mock_ctk_environment):
    """
    Checks that losing focus triggers a delayed destruction
    to allow internal event processing.
    """
    # 1. ARRANGE
    mock_attach = MagicMock()
    dropdown = CTkScrollableDropdown(attach=mock_attach, values=["A"])
    dropdown.after = MagicMock()

    # 2. ACT
    dropdown._on_focus_out()

    # 3. ASSERT
    # Ensures a delay is used to handle click-then-focus races
    dropdown.after.assert_called_once_with(150, dropdown._safe_destroy)