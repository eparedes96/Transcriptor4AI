from __future__ import annotations

"""
Unit tests for Pricing Background Tasks.

Verifies that the pricing update task executes correctly in a 
background thread and invokes the callback with proper results.
Ensures resilience against network exceptions and malformed responses.
"""

from unittest.mock import MagicMock, patch

from transcriptor4ai.interface.gui.threads import run_pricing_update_task


def test_run_pricing_update_task_success() -> None:
    """TC-01: Verify callback execution with valid network data."""
    mock_pricing = {"GPT-4o": {"input_cost_1k": 0.002}}

    with patch("transcriptor4ai.infra.network.fetch_pricing_data", return_value=mock_pricing):
        callback = MagicMock()

        # Execute the task
        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(mock_pricing)


def test_run_pricing_update_task_failure() -> None:
    """TC-02: Verify callback execution with None when network fails."""
    with patch("transcriptor4ai.infra.network.fetch_pricing_data", return_value=None):
        callback = MagicMock()

        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(None)


def test_run_pricing_update_task_exception_handling() -> None:
    """TC-03: Verify that unexpected exceptions in the task return None."""
    # Fix for E501: Multi-line patch to avoid long line length
    with patch(
            "transcriptor4ai.infra.network.fetch_pricing_data",
            side_effect=RuntimeError("DNS Error")
    ):
        callback = MagicMock()

        # Should catch the exception inside and call back with None
        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(None)