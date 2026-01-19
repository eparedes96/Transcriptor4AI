from __future__ import annotations

"""
Unit tests for the CostEstimator service.

Verifies mathematical precision, fallback logic from live to static data,
and resilience against malformed pricing structures.
"""

from typing import Any, Dict

import pytest

from transcriptor4ai.core.services.estimator import CostEstimator


@pytest.fixture
def sample_live_pricing() -> Dict[str, Any]:
    """Provide a sample dynamic pricing dictionary."""
    return {
        "GPT-4o": {"input_cost_1k": 0.005, "output_cost_1k": 0.015},
        "Custom-Model": {"input_cost_1k": 0.010, "output_cost_1k": 0.020}
    }


def test_calculate_cost_with_static_fallback() -> None:
    """TC-01: Verify fallback to AI_MODELS constants when live data is absent."""
    estimator = CostEstimator(live_pricing=None)

    # Using 'ChatGPT 4o' from constants (0.0025 per 1k)
    cost = estimator.calculate_cost(2000, "ChatGPT 4o")
    assert cost == pytest.approx(0.005)


def test_calculate_cost_with_live_overrides(sample_live_pricing: Dict[str, Any]) -> None:
    """TC-02: Verify that live pricing overrides domain constants."""
    estimator = CostEstimator(live_pricing=sample_live_pricing)

    # Live data for GPT-4o is 0.005 per 1k
    cost = estimator.calculate_cost(1000, "GPT-4o")
    assert cost == pytest.approx(0.005)


def test_calculate_cost_handles_missing_model() -> None:
    """TC-03: Verify that unknown models return 0.0 cost safely."""
    estimator = CostEstimator()
    cost = estimator.calculate_cost(1000, "Non-Existent-Model")
    assert cost == 0.0


def test_calculate_cost_zero_or_negative_tokens() -> None:
    """TC-04: Verify handling of zero or negative token counts."""
    estimator = CostEstimator()
    assert estimator.calculate_cost(0, "ChatGPT 4o") == 0.0
    assert estimator.calculate_cost(-100, "ChatGPT 4o") == 0.0


def test_calculate_cost_malformed_data() -> None:
    """TC-05: Verify resilience against non-numeric pricing data."""
    bad_pricing = {"Broken-Model": {"input_cost_1k": "invalid_number"}}
    estimator = CostEstimator(live_pricing=bad_pricing)

    cost = estimator.calculate_cost(1000, "Broken-Model")
    assert cost == 0.0


def test_update_live_pricing(sample_live_pricing: Dict[str, Any]) -> None:
    """TC-06: Verify dynamic update of the pricing table."""
    estimator = CostEstimator()
    estimator.update_live_pricing(sample_live_pricing)

    assert "Custom-Model" in estimator._live_pricing
    assert estimator.calculate_cost(1000, "Custom-Model") == 0.010