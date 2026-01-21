from __future__ import annotations

"""
Unit tests for GUI Handlers (Controller Logic).

Verifies the integration between CustomTkinter views and the AppController,
ensuring data flows correctly from widgets to the internal dynamic model.
Includes financial calculation validation with ModelRegistry (v2.2.0).
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
    mock_app = MagicMock()
    # We mock ModelRegistry to avoid disk IO during controller init
    target = "transcriptor4ai.interface.gui.controllers.main_controller.ModelRegistry"
    with patch(target):
        controller = AppController(mock_app, mock_config_dict, {})

    mock_dash = MagicMock()
    mock_settings = MagicMock()

    # Configure Dashboard Mocks
    mock_dash.entry_input.get.return_value = "/new/input"
    mock_dash.entry_output.get.return_value = "/new/output"
    mock_dash.sw_modules.get.return_value = 0
    mock_dash.sw_tests.get.return_value = 1
    mock_dash.sw_resources.get.return_value = 1

    # Configure Settings Mocks
    mock_settings.entry_ext.get.return_value = ".rs, .toml"
    mock_settings.sw_minify.get.return_value = 1

    controller.register_views(mock_dash, mock_settings, MagicMock(), MagicMock())
    controller.sync_config_from_view()

    assert controller.config["input_path"] == "/new/input"
    assert controller.config["process_modules"] is False
    assert controller.config["minify_output"] is True


@pytest.mark.gui
def test_controller_financial_sync(mock_config_dict: dict) -> None:
    """TC-V2.1-01: Verify estimator and view update upon discovery success."""
    mock_app = MagicMock()
    mock_dash = MagicMock()

    target = "transcriptor4ai.interface.gui.controllers.main_controller.ModelRegistry"
    with patch(target) as mock_reg_cls:
        mock_reg = mock_reg_cls.return_value
        # Simulate a successful live sync
        mock_reg.sync_remote.return_value = True
        mock_reg._is_live_synced = True

        controller = AppController(mock_app, mock_config_dict, {})
        controller.register_views(mock_dash, MagicMock(), MagicMock(), MagicMock())

        # Discovery completion (data ignored in new registry-driven logic)
        controller.on_pricing_updated({})

        # Verify visual status was updated to LIVE
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
    """
    mock_app = MagicMock()
    mock_dash = MagicMock()

    mock_config_dict["target_model"] = "ChatGPT 4o"

    target = "transcriptor4ai.interface.gui.controllers.main_controller.ModelRegistry"
    with patch(target) as mock_reg_cls:
        mock_reg = mock_reg_cls.return_value
        # Inject model data into the registry mock
        mock_reg.get_model_info.return_value = {
            "input_cost_1k": 0.0025,
            "context_window": 128000
        }

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

        # Verify calculation was dispatched to UI
        mock_dash.update_cost_display.assert_called_with(0.025)


@pytest.mark.gui
def test_open_file_explorer_calls_system(tmp_path: Path) -> None:
    """Verify OS-specific command dispatch for file exploration."""
    target_dir = tmp_path / "target"
    target_dir.mkdir()
    path_str = str(target_dir)

    with patch("platform.system", return_value="Windows"):
        with patch("os.startfile", create=True) as mock_start:
            open_file_explorer(path_str)
            mock_start.assert_called_with(path_str)

    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.Popen") as mock_popen:
            open_file_explorer(path_str)
            mock_popen.assert_called_with(["xdg-open", path_str])