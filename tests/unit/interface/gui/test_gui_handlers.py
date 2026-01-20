from __future__ import annotations

"""
Unit tests for GUI Handlers (Controller Logic).

Verifies the integration between CustomTkinter views and the AppController,
ensuring data flows correctly from widgets to the internal configuration model.
Includes OS-specific interaction tests and financial integration (v2.1.0).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from transcriptor4ai.domain.pipeline_models import create_success_result
from transcriptor4ai.interface.gui.controllers.main_controller import AppController
from transcriptor4ai.interface.gui.utils.tk_helpers import (
    open_file_explorer,
    parse_list_from_string,
)


@pytest.mark.gui
def test_parse_list_from_string_gui() -> None:
    """Verify helper splits CSV strings from GUI inputs into clean lists."""
    assert parse_list_from_string(".py, .js") == [".py", ".js"]
    assert parse_list_from_string("  val1  , val2 ") == ["val1", "val2"]
    assert parse_list_from_string("") == []
    assert parse_list_from_string(None) == []


@pytest.mark.gui
def test_controller_sync_config_from_view(mock_config_dict: dict) -> None:
    """
    Verify that the AppController correctly scrapes values from
    CustomTkinter widgets and updates the config dictionary.
    """
    # 1. Setup Controller with mocks
    mock_app = MagicMock()
    mock_app_state = {}
    controller = AppController(mock_app, mock_config_dict, mock_app_state)

    # 2. Mock Views & Widgets
    mock_dash = MagicMock()
    mock_settings = MagicMock()

    # Configure Dashboard Mocks (Simulate User Input)
    mock_dash.entry_input.get.return_value = "/new/input"
    mock_dash.entry_output.get.return_value = "/new/output"
    mock_dash.entry_subdir.get.return_value = "new_sub"
    mock_dash.entry_prefix.get.return_value = "new_prefix"

    # Simulate Switches (1=True, 0=False in CTK)
    mock_dash.sw_modules.get.return_value = 0
    mock_dash.sw_tests.get.return_value = 1
    mock_dash.sw_resources.get.return_value = 1
    mock_dash.sw_tree.get.return_value = 1

    # Simulate AST Checkboxes
    mock_dash.chk_func.get.return_value = 1
    mock_dash.chk_class.get.return_value = 0
    mock_dash.chk_meth.get.return_value = 0

    # Configure Settings Mocks
    mock_settings.entry_ext.get.return_value = ".rs, .toml"
    mock_settings.entry_inc.get.return_value = "src/.*"
    mock_settings.entry_exc.get.return_value = ""

    mock_settings.sw_gitignore.get.return_value = 1
    mock_settings.sw_individual.get.return_value = 1
    mock_settings.sw_unified.get.return_value = 0
    mock_settings.sw_sanitizer.get.return_value = 1
    mock_settings.sw_mask.get.return_value = 0
    mock_settings.sw_minify.get.return_value = 1
    mock_settings.sw_error_log.get.return_value = 0

    # Register mocks with controller
    controller.register_views(mock_dash, mock_settings, MagicMock(), MagicMock())

    # 3. Execute Sync
    controller.sync_config_from_view()

    # 4. Assertions
    # Check Paths
    assert controller.config["input_path"] == "/new/input"

    # Check Logic Flags
    assert controller.config["process_modules"] is False
    assert controller.config["minify_output"] is True


@pytest.mark.gui
def test_controller_financial_sync(mock_config_dict: dict) -> None:
    """TC-V2.1-01: Verify estimator and view update upon pricing sync success."""
    mock_app = MagicMock()
    mock_dash = MagicMock()
    controller = AppController(mock_app, mock_config_dict, {})
    controller.register_views(mock_dash, MagicMock(), MagicMock(), MagicMock())

    # Raw LiteLLM data format (input_cost_per_token)
    pricing_data = {
        "Model-X": {
            "input_cost_per_token": 0.00005,
            "litellm_provider": "openai"
        }
    }
    controller.on_pricing_updated(pricing_data)

    # Expected internal adapted format
    expected_adapted = {
        "Model-X": {
            "id": "Model-X",
            "input_cost_1k": 0.05,
            "provider": "openai"
        }
    }

    assert controller.cost_estimator._live_pricing == expected_adapted
    mock_dash.set_pricing_status.assert_called_with(is_live=True)


@pytest.mark.gui
@patch("transcriptor4ai.interface.gui.controllers.main_controller.results_modal.show_results_window")
@patch("transcriptor4ai.interface.gui.controllers.main_controller.mb")
def test_controller_result_cost_calc(
        mock_mb: MagicMock,
        mock_show_results: MagicMock,
        mock_config_dict: dict
) -> None:
    """
    TC-V2.1-02: Verify cost calculation is triggered after pipeline success.

    Ensures that the controller uses a valid model key to perform calculations.
    """
    mock_app = MagicMock()
    mock_dash = MagicMock()

    # Ensure config uses a valid model key existing in constants.py
    mock_config_dict["target_model"] = "ChatGPT 4o"

    controller = AppController(mock_app, mock_config_dict, {})
    controller.register_views(mock_dash, MagicMock(), MagicMock(), MagicMock())

    # Result with 10k tokens -> Cost: (10000/1000) * 0.0025 = 0.025
    result = create_success_result(
        cfg=mock_config_dict,
        base_path="/in",
        final_output_path="/out",
        existing_files=[],
        token_count=10000
    )

    controller._handle_process_result(result)

    # 1. Verify the dashboard was updated with the correct calculation
    mock_dash.update_cost_display.assert_called_with(0.025)

    # 2. Verify the modal was requested but not physically shown
    mock_show_results.assert_called_once()


@pytest.mark.gui
def test_open_file_explorer_calls_system(tmp_path: Path) -> None:
    """Verify that the correct OS command is called based on platform."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    path_str = str(target_dir)

    # Test Windows
    with patch("platform.system", return_value="Windows"):
        with patch("os.startfile", create=True) as mock_start:
            open_file_explorer(path_str)
            mock_start.assert_called_with(path_str)

    # Test Linux
    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.Popen") as mock_popen:
            open_file_explorer(path_str)
            mock_popen.assert_called_with(["xdg-open", path_str])


@pytest.mark.gui
def test_open_file_explorer_handles_invalid_path() -> None:
    """It should verify path existence before calling system to avoid crashes."""
    # Mock showerror to avoid UI popup during test
    with patch("tkinter.messagebox.showerror") as mock_alert:
        with patch("subprocess.Popen") as mock_popen:
            open_file_explorer("/non/existent/path")
            mock_popen.assert_not_called()
            mock_alert.assert_called_once()