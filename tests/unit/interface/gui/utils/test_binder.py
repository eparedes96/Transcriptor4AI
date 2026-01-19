from __future__ import annotations

"""
Unit tests for the UI Form Binder.

Verifies the declarative mapping between configuration keys and
CustomTkinter widgets, and ensures thread-safe widget state manipulation.
"""

from unittest.mock import MagicMock

import pytest

from transcriptor4ai.interface.gui.utils.binder import FormBinder


@pytest.fixture
def binder() -> FormBinder:
    """Return a fresh FormBinder instance."""
    return FormBinder()


@pytest.fixture
def mock_widgets() -> tuple[MagicMock, MagicMock]:
    """Create mock dashboard and settings views with necessary widgets."""
    dashboard = MagicMock()
    settings = MagicMock()

    # Mock dashboard widgets
    dashboard.sw_modules = MagicMock()
    dashboard.sw_tests = MagicMock()
    dashboard.sw_resources = MagicMock()
    dashboard.sw_tree = MagicMock()
    dashboard.chk_func = MagicMock()
    dashboard.chk_class = MagicMock()
    dashboard.chk_meth = MagicMock()
    dashboard.entry_subdir = MagicMock()
    dashboard.entry_prefix = MagicMock()

    # Mock settings widgets
    settings.sw_gitignore = MagicMock()
    settings.sw_individual = MagicMock()
    settings.sw_unified = MagicMock()
    settings.sw_sanitizer = MagicMock()
    settings.sw_mask = MagicMock()
    settings.sw_minify = MagicMock()
    settings.sw_error_log = MagicMock()

    return dashboard, settings


def test_get_ui_mapping_completeness(
    binder: FormBinder,
    mock_widgets: tuple[MagicMock, MagicMock]
) -> None:
    """Verify that all expected configuration keys are present in the mapping."""
    dash, sett = mock_widgets
    mapping = binder.get_ui_mapping(dash, sett)

    assert "switches" in mapping
    assert "checkboxes" in mapping
    assert "entries" in mapping

    # Check key presence in switches
    switch_keys = [item[0] for item in mapping["switches"]]
    assert "process_modules" in switch_keys
    assert "enable_sanitizer" in switch_keys
    assert "minify_output" in switch_keys


def test_update_entry_readonly_bypass(binder: FormBinder) -> None:
    """Verify that update_entry handles the state lifecycle of CTkEntry."""
    mock_entry = MagicMock()
    test_text = "new_path/project"

    binder.update_entry(mock_entry, test_text)

    # Sequence check: Normal -> Delete -> Insert -> Readonly
    mock_entry.configure.assert_any_call(state="normal")
    mock_entry.delete.assert_called_once_with(0, "end")
    mock_entry.insert.assert_called_once_with(0, test_text)
    mock_entry.configure.assert_any_call(state="readonly")


def test_set_switch_state_logic(binder: FormBinder) -> None:
    """Verify CTkSwitch selection logic based on config booleans."""
    mock_switch = MagicMock()
    config_true = {"feat_enabled": True}
    config_false = {"feat_enabled": False}

    binder.set_switch_state(config_true, mock_switch, "feat_enabled")
    mock_switch.select.assert_called_once()

    binder.set_switch_state(config_false, mock_switch, "feat_enabled")
    mock_switch.deselect.assert_called_once()


def test_set_checkbox_state_logic(binder: FormBinder) -> None:
    """Verify CTkCheckBox selection logic based on config booleans."""
    mock_chk = MagicMock()
    config = {"show_stuff": True}

    binder.set_checkbox_state(config, mock_chk, "show_stuff")
    mock_chk.select.assert_called_once()