from __future__ import annotations

"""
Unit tests for GUI Handlers (Controller Logic).

Verifies the integration between CustomTkinter views and the AppController,
ensuring data flows correctly from widgets to the internal dynamic model.
Includes financial calculation validation with ModelRegistry (v2.1.0).
"""

from unittest.mock import MagicMock, patch

import pytest

from transcriptor4ai.interface.gui.controllers.main_controller import AppController


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


