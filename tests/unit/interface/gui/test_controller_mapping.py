from __future__ import annotations

"""
Unit tests for the GUI Controller Mapping logic.

Tests the mapping between UI toggle switches and the internal 
'processing_depth' state to prevent invalid configuration combinations.
"""

from unittest.mock import MagicMock

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