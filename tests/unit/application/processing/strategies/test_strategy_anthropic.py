import os

import pytest

from transcriptor4ai.application.processing.strategies.anthropic import AnthropicApiStrategy

# ==============================================================================
# TEST GROUP: ANTHROPIC TOKENIZATION STRATEGY
# ==============================================================================

@pytest.fixture
def mock_anthropic_client(mocker):
    """Mocks the Anthropic SDK client structure."""
    mock_client = mocker.Mock()
    # Mocking the path client.beta.messages.count_tokens
    mock_count_response = mocker.Mock()
    mock_count_response.input_tokens = 42
    mock_client.beta.messages.count_tokens.return_value = mock_count_response

    return mocker.patch("anthropic.Anthropic", return_value=mock_client)


@pytest.fixture
def strategy():
    """Provides a fresh instance of the strategy."""
    return AnthropicApiStrategy()


@pytest.mark.unit
def test_should_raise_import_error_when_sdk_missing(mocker, strategy):
    """Ensures the strategy fails gracefully if the library is not installed."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.anthropic.ANTHROPIC_AVAILABLE", False)

    # 2. ACT & 3. ASSERT
    with pytest.raises(ImportError, match="anthropic' is not installed"):
        strategy.count("some text", "claude-3")


@pytest.mark.unit
def test_should_raise_value_error_when_api_key_missing(mocker, strategy):
    """Validates that the strategy requires an environment API key to function."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.anthropic.ANTHROPIC_AVAILABLE", True)
    mocker.patch.dict(os.environ, {}, clear=True)

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY missing"):
        strategy.count("some text", "claude-3")


@pytest.mark.unit
@pytest.mark.parametrize("input_model, expected_api_id", [
    ("claude-3.5-sonnet", "claude-3-5-sonnet-20240620"),
    ("claude-3-opus", "claude-3-opus-20240229"),
    ("claude-4.5-haiku", "claude-haiku-4-5-20251001"),
    ("claude-4.5-opus", "claude-opus-4-5-20251101"),
    ("claude-4.5-sonnet", "claude-sonnet-4-5-20250929"),
    ("unknown-model", "claude-3-5-sonnet-20240620"),  # Default fallback in SUT
])
def test_should_map_logical_ids_to_correct_anthropic_api_models(
        mocker, mock_anthropic_client, strategy, input_model, expected_api_id
):
    """Verifies that internal regex/string logic selects the right model for the API call."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.anthropic.ANTHROPIC_AVAILABLE", True)
    mocker.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-123"})
    client_instance = mock_anthropic_client.return_value

    # 2. ACT
    tokens = strategy.count("Sample payload", input_model)

    # 3. ASSERT
    assert tokens == 42
    client_instance.beta.messages.count_tokens.assert_called_once()

    # Verify the model used in the call matches expectation
    kwargs = client_instance.beta.messages.count_tokens.call_args.kwargs
    assert kwargs["model"] == expected_api_id
    assert kwargs["messages"][0]["content"] == "Sample payload"


@pytest.mark.unit
def test_should_propagate_anthropic_api_exceptions(mocker, mock_anthropic_client, strategy):
    """Ensures that technical API failures are logged and propagated upwards."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.anthropic.ANTHROPIC_AVAILABLE", True)
    mocker.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test-123"})

    client_instance = mock_anthropic_client.return_value
    client_instance.beta.messages.count_tokens.side_effect = Exception("API Overloaded")

    mock_logger = mocker.patch("transcriptor4ai.application.processing.strategies.anthropic.logger.error")

    # 2. ACT & 3. ASSERT
    with pytest.raises(Exception, match="API Overloaded"):
        strategy.count("text", "claude-3.5")

    # Critical point: Ensure the error was logged for diagnostics
    mock_logger.assert_called_once()