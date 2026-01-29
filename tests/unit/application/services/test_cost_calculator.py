from __future__ import annotations

# ==============================================================================
# TEST GROUP: COST CALCULATOR SERVICE
# ==============================================================================

import pytest
from transcriptor4ai.application.services.cost_calculator import CostCalculatorService


@pytest.fixture
def mock_registry(mocker):
    """Provides a mock implementation of the IModelRegistry port."""
    registry = mocker.Mock()

    # Default behavior for known models using side_effect
    registry.get_model_info.side_effect = lambda name: {
        "gpt-4o": {"input_cost_1k": 0.005, "context_window": 128000},
        "claude-3-5-sonnet": {"input_cost_1k": 0.003, "context_window": 200000},
    }.get(name)

    return registry


@pytest.fixture
def calculator(mock_registry):
    """Provides a CostCalculatorService instance with an injected mock registry."""
    return CostCalculatorService(mock_registry)


@pytest.mark.unit
def test_calculate_cost_standard_precision(calculator):
    """
    Verifies the financial formula: (tokens / 1000) * price_per_1k.
    Example: 2000 tokens at $0.005/1k should equal $0.01.
    """
    # 1. ARRANGE
    tokens = 2000
    model = "gpt-4o"
    expected_usd = 0.01

    # 2. ACT
    result = calculator.calculate_cost(tokens, model)

    # 3. ASSERT
    assert result == pytest.approx(expected_usd)


@pytest.mark.unit
def test_calculate_cost_uses_precalculated_override(calculator):
    """
    Ensures that precalculated tokens (e.g., from SQLite cache) take precedence
    over live token counts to maintain consistency across runs.
    """
    # 1. ARRANGE
    live_tokens = 5000  # Should be ignored
    cached_tokens = 1000
    model = "gpt-4o"
    # (1000 / 1000) * 0.005 = 0.005
    expected_usd = 0.005

    # 2. ACT
    result = calculator.calculate_cost(live_tokens, model, precalculated_tokens=cached_tokens)

    # 3. ASSERT
    assert result == pytest.approx(expected_usd)


@pytest.mark.unit
def test_calculate_cost_returns_zero_on_unknown_model(calculator, mock_registry):
    """
    Safety check: If the registry returns None for a model, the cost must
    be 0.0 instead of raising a KeyError or TypeError.
    """
    # 1. ARRANGE
    # We use a name that the side_effect lambda won't find in its dict
    model_name = "non-existent-ai"

    # 2. ACT
    result = calculator.calculate_cost(1000, model_name)

    # 3. ASSERT
    assert result == 0.0


@pytest.mark.unit
@pytest.mark.parametrize("tokens", [0, -100, None])
def test_calculate_cost_handles_invalid_token_counts(calculator, tokens):
    """
    Validates that zero, negative or null token counts result in
    zero cost without crashing the service.

    NOTE: For this test to pass with 'None', the SUT (cost_calculator.py)
    must sanitize the input (e.g., tokens or 0).
    """
    # 2. ACT
    result = calculator.calculate_cost(tokens, "gpt-4o")  # type: ignore

    # 3. ASSERT
    assert result == 0.0


@pytest.mark.unit
def test_get_context_window_returns_correct_limit(calculator):
    """
    Verifies that the service retrieves the correct context limit
    from the registry metadata.
    """
    # 2. ACT & 3. ASSERT
    assert calculator.get_context_window("gpt-4o") == 128000
    assert calculator.get_context_window("claude-3-5-sonnet") == 200000


@pytest.mark.unit
def test_get_context_window_fallback_on_missing_data(calculator, mock_registry):
    """
    Ensures a safe default context window (4096) is returned if the model
    info is missing or corrupted.
    """
    # 1. ARRANGE
    # Ensure side_effect is None so we can return a specific value
    mock_registry.get_model_info.side_effect = None
    mock_registry.get_model_info.return_value = None

    # 2. ACT
    limit = calculator.get_context_window("unknown-model")

    # 3. ASSERT
    assert limit == 4096


@pytest.mark.unit
def test_sync_remote_data_delegation(calculator, mock_registry):
    """
    Verifies that the sync call is correctly delegated to the model
    registry port and returns its status.
    """
    # 1. ARRANGE
    mock_registry.sync_remote.return_value = True

    # 2. ACT
    success = calculator.sync_remote_data()

    # 3. ASSERT
    mock_registry.sync_remote.assert_called_once()
    assert success is True


@pytest.mark.unit
def test_calculate_cost_resilience_to_malformed_prices(calculator, mock_registry):
    """
    Ensures that if the price in the registry is not a valid number,
    the calculator fails gracefully returning 0.0 cost.
    """
    # 1. ARRANGE
    # CRITICAL: We must clear the side_effect from the fixture to allow
    # the return_value to take effect.
    mock_registry.get_model_info.side_effect = None
    mock_registry.get_model_info.return_value = {"input_cost_1k": "free_tier"}

    # 2. ACT
    result = calculator.calculate_cost(1000, "gpt-4o")

    # 3. ASSERT
    assert result == 0.0