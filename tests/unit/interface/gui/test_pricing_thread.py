from __future__ import annotations

"""
Unit tests for Pricing Background Tasks.

Verifies that the model discovery task executes correctly in a 
background thread and invokes the callback with proper results.
Ensures resilience against network exceptions and name changes in the API.
"""

from unittest.mock import MagicMock, patch

from transcriptor4ai.interface.gui.threads import run_pricing_update_task


def test_run_pricing_update_task_success() -> None:
    """TC-01: Verify callback execution with valid network data."""
    mock_data = {"GPT-4o": {"input_cost_per_token": 0.0000025}}

    # FIX: Patched fetch_external_model_data (new API name)
    target = "transcriptor4ai.infra.network.fetch_external_model_data"
    with patch(target, return_value=mock_data):
        callback = MagicMock()

        # Execute the task
        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(mock_data)


def test_run_pricing_update_task_failure() -> None:
    """TC-02: Verify callback execution with None when network fails."""
    target = "transcriptor4ai.infra.network.fetch_external_model_data"
    with patch(target, return_value=None):
        callback = MagicMock()

        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(None)


def test_run_pricing_update_task_exception_handling() -> None:
    """TC-03: Verify that unexpected exceptions in the task return None."""
    target = "transcriptor4ai.infra.network.fetch_external_model_data"
    with patch(target, side_effect=RuntimeError("DNS Error")):
        callback = MagicMock()

        # Should catch the exception inside and call back with None
        run_pricing_update_task(on_complete=callback)

        callback.assert_called_once_with(None)