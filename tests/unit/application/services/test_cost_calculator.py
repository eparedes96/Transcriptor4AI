from __future__ import annotations

"""
Unit tests for the CostEstimator service.

Verifies mathematical precision, dynamic registry integration,
context limit retrieval, and resilience against missing model metadata.
"""

from unittest.mock import MagicMock

import pytest

from transcriptor4ai.core.services.estimator import CostEstimator


@pytest.fixture
def mock_registry() -> MagicMock:
    """Provide a mock ModelRegistry with sample data."""
    registry = MagicMock()
    # Mock behavior for known models
    registry.get_model_info.side_effect = lambda m: {
        "gpt-4o": {"input_cost_1k": 0.0025, "context_window": 128000},
        "claude-3-5": {"input_cost_1k": 0.003, "context_window": 200000},
    }.get(m)
    return registry


def test_calculate_cost_with_registry_data(mock_registry: MagicMock) -> None:
    """TC-01: Verify cost calculation using dynamic registry metadata."""
    estimator = CostEstimator(registry=mock_registry)

    # 2000 tokens of gpt-4o -> (2000/1000) * 0.0025 = 0.005 USD
    cost = estimator.calculate_cost(2000, "gpt-4o")
    assert cost == pytest.approx(0.005)


def test_calculate_cost_with_precalculated_tokens(mock_registry: MagicMock) -> None:
    """TC-02: Verify that precalculated tokens (from cache) override metrics."""
    estimator = CostEstimator(registry=mock_registry)

    # Even if current tokens are 0, use precalculated 4000
    cost = estimator.calculate_cost(0, "gpt-4o", precalculated_tokens=4000)
    assert cost == pytest.approx(0.01)


def test_calculate_cost_handles_missing_model(mock_registry: MagicMock) -> None:
    """TC-03: Verify that unknown models return 0.0 cost safely."""
    estimator = CostEstimator(registry=mock_registry)
    cost = estimator.calculate_cost(1000, "non-existent-model")
    assert cost == 0.0


def test_calculate_cost_zero_or_negative_tokens(mock_registry: MagicMock) -> None:
    """TC-04: Verify handling of zero or negative token counts."""
    estimator = CostEstimator(registry=mock_registry)
    assert estimator.calculate_cost(0, "gpt-4o") == 0.0
    assert estimator.calculate_cost(-100, "gpt-4o") == 0.0


def test_get_context_limit(mock_registry: MagicMock) -> None:
    """TC-05: Verify context limit retrieval from registry."""
    estimator = CostEstimator(registry=mock_registry)

    assert estimator.get_context_limit("gpt-4o") == 128000
    assert estimator.get_context_limit("claude-3-5") == 200000
    # Default fallback if unknown
    assert estimator.get_context_limit("unknown") == 4096


def test_update_live_pricing_delegation(mock_registry: MagicMock) -> None:
    """TC-06: Verify that the estimator delegates sync to the registry."""
    estimator = CostEstimator(registry=mock_registry)

    estimator.update_live_pricing()
    mock_registry.sync_remote.assert_called_once()