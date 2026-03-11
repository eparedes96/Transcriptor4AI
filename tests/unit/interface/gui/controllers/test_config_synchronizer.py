from __future__ import annotations

# ==============================================================================
# TEST GROUP: CONFIGURATION SYNCHRONIZER
# ==============================================================================
import pytest

from transcriptor4ai.interface.gui.controllers.config_synchronizer import ConfigSynchronizer


@pytest.fixture
def mock_coordinator(mocker, mock_config_dict):
    """
    Creates a full mock of the AppController with nested views and widgets.
    """
    coordinator = mocker.Mock()
    coordinator.config = mock_config_dict.copy()

    # 1. ARRANGE: Mock Dashboard Widgets
    dash = mocker.Mock()
    dash.entry_input = mocker.Mock()
    dash.entry_output = mocker.Mock()
    dash.entry_subdir = mocker.Mock()
    dash.entry_prefix = mocker.Mock()
    dash.sw_modules = mocker.Mock()
    dash.sw_tree = mocker.Mock()
    dash.sw_skeleton = mocker.Mock()
    dash.chk_func = mocker.Mock()
    dash.chk_class = mocker.Mock()
    dash.chk_meth = mocker.Mock()

    # 2. ARRANGE: Mock Settings Widgets
    sett = mocker.Mock()
    sett.entry_ext = mocker.Mock()
    sett.entry_inc = mocker.Mock()
    sett.entry_exc = mocker.Mock()
    sett.sw_gitignore = mocker.Mock()
    sett.sw_individual = mocker.Mock()
    sett.sw_unified = mocker.Mock()
    sett.sw_sanitizer = mocker.Mock()
    sett.sw_mask = mocker.Mock()
    sett.sw_minify = mocker.Mock()
    sett.sw_error_log = mocker.Mock()
    sett.combo_profiles = mocker.Mock()
    sett.combo_stack = mocker.Mock()
    sett.combo_provider = mocker.Mock()
    sett.combo_model = mocker.Mock()

    coordinator.dashboard_view = dash
    coordinator.settings_view = sett

    # Mock model registry behavior
    coordinator.get_model_registry().get_available_models.return_value = {
        "gpt-4o": {"provider": "OPENAI"}
    }
    coordinator.get_model_registry().get_model_info.return_value = {"provider": "OPENAI"}

    return coordinator


@pytest.mark.unit
def test_sync_to_view_populates_all_widget_types(mock_coordinator):
    """
    Verifies that standard configuration values are correctly pushed
    to the UI widgets (Entries, Switches, Checkboxes).
    """
    # 1. ARRANGE
    sync = ConfigSynchronizer(mock_coordinator)
    mock_coordinator.config["output_prefix"] = "sync_test"
    mock_coordinator.config["minify_output"] = True

    # 2. ACT
    sync.sync_to_view()

    # 3. ASSERT: Verify Entry update (normalizes state to write)
    mock_coordinator.dashboard_view.entry_prefix.insert.assert_called_with(0, "sync_test")
    # Verify Switch update
    mock_coordinator.settings_view.sw_minify.select.assert_called_once()


@pytest.mark.unit
@pytest.mark.parametrize("depth, modules_selected, skeleton_selected", [
    ("full", True, False),
    ("skeleton", True, True),
    ("tree_only", False, False),
])
def test_sync_to_view_maps_processing_depth_logic(mock_coordinator, depth, modules_selected, skeleton_selected):
    """
    Validates the complex mapping between the 'processing_depth' domain string
    and the multiple UI switches in the dashboard.
    """
    # 1. ARRANGE
    sync = ConfigSynchronizer(mock_coordinator)
    mock_coordinator.config["processing_depth"] = depth

    # 2. ACT
    sync.sync_to_view()

    # 3. ASSERT
    # Check Modules Switch
    if modules_selected:
        mock_coordinator.dashboard_view.sw_modules.select.assert_called()
    else:
        mock_coordinator.dashboard_view.sw_modules.deselect.assert_called()

    # Check Skeleton Switch
    if skeleton_selected:
        mock_coordinator.dashboard_view.sw_skeleton.select.assert_called()
    else:
        mock_coordinator.dashboard_view.sw_skeleton.deselect.assert_called()


@pytest.mark.unit
def test_sync_from_view_updates_config_dict(mock_coordinator):
    """
    Ensures that user input in widgets is correctly scraped and
    stored back into the configuration dictionary.
    """
    # 1. ARRANGE
    sync = ConfigSynchronizer(mock_coordinator)
    # Configure mocks to return specific user input
    mock_coordinator.dashboard_view.entry_prefix.get.return_value = "new_prefix"
    mock_coordinator.dashboard_view.sw_modules.get.return_value = 1
    mock_coordinator.dashboard_view.sw_skeleton.get.return_value = 0
    mock_coordinator.settings_view.entry_ext.get.return_value = ".py, .ts"
    mock_coordinator.settings_view.combo_model.get.return_value = "gpt-4o"

    # 2. ACT
    sync.sync_from_view()

    # 3. ASSERT
    assert mock_coordinator.config["output_prefix"] == "new_prefix"
    assert mock_coordinator.config["processing_depth"] == "full"
    assert mock_coordinator.config["extensions"] == [".py", ".ts"]
    assert mock_coordinator.config["target_model"] == "gpt-4o"


@pytest.mark.unit
def test_sync_from_view_handles_csv_whitespace(mock_coordinator):
    """
    Robustness check: CSV fields like extensions or patterns should
    be trimmed to avoid filtering errors.
    """
    # 1. ARRANGE
    sync = ConfigSynchronizer(mock_coordinator)
    mock_coordinator.settings_view.entry_ext.get.return_value = " .py ,  .js  "

    # 2. ACT
    sync.sync_from_view()

    # 3. ASSERT
    assert mock_coordinator.config["extensions"] == [".py", ".js"]


@pytest.mark.unit
def test_sync_to_view_aborts_if_views_missing(mock_coordinator):
    """
    Safety check: The synchronizer should not crash if views are not
    yet registered in the coordinator.
    """
    # 1. ARRANGE
    mock_coordinator.dashboard_view = None
    sync = ConfigSynchronizer(mock_coordinator)

    # 2. ACT & 3. ASSERT
    # Should not raise AttributeError
    sync.sync_to_view()