from __future__ import annotations

"""
Unit tests for the FormBinder utility.

Ensures bidirectional synchronization between Domain Configuration 
and CustomTkinter UI components is consistent and fault-tolerant.
"""


import pytest

from transcriptor4ai.interface.gui.common.form_binder import FormBinder

# ==============================================================================
# TEST GROUP: UI COMPONENT BINDING LOGIC
# ==============================================================================

@pytest.fixture
def binder() -> FormBinder:
    return FormBinder()


def test_update_entry_bypasses_readonly_state(mocker, binder):
    """
    Ensures that Entry widgets are temporarily unlocked to update content
    and then returned to their protective 'readonly' state.
    """
    # 1. ARRANGE
    mock_entry = mocker.Mock()
    test_text = "new/path/test"

    # 2. ACT
    binder.update_entry(mock_entry, test_text)

    # 3. ASSERT
    # Must change state to normal to allow editing
    mock_entry.configure.assert_any_call(state="normal")
    # Must clear previous content and insert new
    mock_entry.delete.assert_called_once_with(0, "end")
    mock_entry.insert.assert_called_once_with(0, test_text)
    # Must return to readonly to prevent accidental user typing
    mock_entry.configure.assert_called_with(state="readonly")


@pytest.mark.parametrize("config_value, expected_method", [
    (True, "select"),
    (False, "deselect"),
    (1, "select"),
    (0, "deselect"),
])
def test_set_switch_state_syncs_boolean_values(mocker, binder, config_value, expected_method):
    """
    Verifies that CTkSwitch widgets are toggled correctly based on
    the truthiness of the configuration values.
    """
    # 1. ARRANGE
    mock_switch = mocker.Mock()
    config = {"test_key": config_value}

    # 2. ACT
    binder.set_switch_state(config, mock_switch, "test_key")

    # 3. ASSERT
    getattr(mock_switch, expected_method).assert_called_once()


def test_set_checkbox_state_handles_missing_keys(mocker, binder):
    """
    Ensures the binder defaults to 'False' (deselect) if the
    requested key is missing from the configuration dictionary.
    """
    # 1. ARRANGE
    mock_chk = mocker.Mock()
    empty_config = {}

    # 2. ACT
    binder.set_checkbox_state(empty_config, mock_chk, "non_existent_key")

    # 3. ASSERT
    mock_chk.deselect.assert_called_once()
    mock_chk.select.assert_not_called()


# ==============================================================================
# TEST GROUP: UI MAPPING INTEGRITY
# ==============================================================================

def test_get_ui_mapping_structure_completeness(mocker, binder):
    """
    Validates that the mapping function returns all required widget groups
    to support the full synchronization cycle.
    """
    # 1. ARRANGE
    # Mock views to simulate the dashboard and settings frames
    mock_dash = mocker.Mock()
    mock_sett = mocker.Mock()

    # 2. ACT
    mapping = binder.get_ui_mapping(mock_dash, mock_sett)

    # 3. ASSERT
    assert "switches" in mapping
    assert "checkboxes" in mapping
    assert "entries" in mapping

    # Check if critical modules are included in the mapping
    switch_keys = [item[0] for item in mapping["switches"]]
    assert "process_modules" in switch_keys
    assert "enable_sanitizer" in switch_keys


def test_get_ui_mapping_returns_empty_on_null_views(binder):
    """
    Resilience check: If views are not yet initialized or passed as None,
    the binder should return an empty dict instead of raising AttributeError.
    """
    # 1. ARRANGE & 2. ACT
    mapping = binder.get_ui_mapping(None, None)

    # 3. ASSERT
    assert mapping == {}