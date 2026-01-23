from __future__ import annotations

import pytest

from transcriptor4ai.domain.entities.pipeline_results import create_success_result

"""
Unit tests for the GUI Controller Mapping logic.

Tests the mapping between UI toggle switches and the internal 
'processing_depth' state to prevent invalid configuration combinations.
"""

from unittest.mock import MagicMock, patch

from transcriptor4ai.interface.gui.controllers.main_controller import AppController


def test_controller_depth_routing_logic() -> None:
    """
    TC-01: Verify UI switch combinations map to correct processing_depth.
    """
    # Mock App and State
    mock_app = MagicMock()
    mock_config = {"processing_depth": "full", "process_modules": True}

    controller = AppController(mock_app, mock_config, {})

    # Mock View Components
    mock_dashboard = MagicMock()
    mock_settings = MagicMock()
    controller.register_views(mock_dashboard, mock_settings, MagicMock(), MagicMock())

    # Case A: Modules OFF -> depth = tree_only (Regardless of Skeleton switch)
    mock_dashboard.sw_modules.get.return_value = 0
    mock_dashboard.sw_skeleton.get.return_value = 1
    controller.sync_config_from_view()
    assert controller.config["processing_depth"] == "tree_only"

    # Case B: Modules ON + Skeleton ON -> depth = skeleton
    mock_dashboard.sw_modules.get.return_value = 1
    mock_dashboard.sw_skeleton.get.return_value = 1
    controller.sync_config_from_view()
    assert controller.config["processing_depth"] == "skeleton"

    # Case C: Modules ON + Skeleton OFF -> depth = full
    mock_dashboard.sw_modules.get.return_value = 1
    mock_dashboard.sw_skeleton.get.return_value = 0
    controller.sync_config_from_view()
    assert controller.config["processing_depth"] == "full"


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
