import os

import pytest

from transcriptor4ai.application.processing.strategies.google import GoogleApiStrategy

# ==============================================================================
# TEST GROUP: GOOGLE GEMINI TOKENIZATION STRATEGY
# ==============================================================================

@pytest.fixture
def mock_google_client(mocker):
    """
    Mocks the Google GenAI SDK by forcing the creation of the 'genai' attribute.

    CRITICAL FIX: Since 'genai' is imported inside a try-except, it might not
    exist in the module namespace if the library is not installed.
    'create=True' forces the injection of the mock into the SUT.
    """
    # 1. ARRANGE: Create the hierarchy of mocks
    mock_genai_module = mocker.Mock()
    mock_client_instance = mocker.Mock()
    mock_response = mocker.Mock()

    # Configure the response
    mock_response.total_token_count = 123

    # Chain the mocks: genai.Client() -> client; client.models.count_tokens() -> response
    mock_genai_module.Client.return_value = mock_client_instance
    mock_client_instance.models.count_tokens.return_value = mock_response

    # Inject the mock into the module even if 'genai' was never imported
    mocker.patch(
        "transcriptor4ai.application.processing.strategies.google.genai",
        mock_genai_module,
        create=True
    )

    return mock_client_instance


@pytest.fixture
def strategy():
    """Provides a fresh instance of the GoogleApiStrategy."""
    return GoogleApiStrategy()


# ------------------------------------------------------------------------------
# SCENARIO: Dependency and Configuration Failures
# ------------------------------------------------------------------------------

@pytest.mark.unit
def test_should_raise_import_error_when_google_sdk_is_missing(mocker, strategy):
    """Ensures a clean failure if the 'google-genai' library is not available."""
    # 1. ARRANGE: Set the availability flag to False
    mocker.patch("transcriptor4ai.application.processing.strategies.google.GOOGLE_AVAILABLE", False)

    # 2. ACT & 3. ASSERT
    with pytest.raises(ImportError, match="google-genai' is not installed"):
        strategy.count("text", "gemini-1.5")


@pytest.mark.unit
def test_should_raise_value_error_when_google_api_key_is_missing(mocker, strategy):
    """Validates that an API key is strictly required for remote counting."""
    # 1. ARRANGE: Mock library as present but environment as empty
    mocker.patch("transcriptor4ai.application.processing.strategies.google.GOOGLE_AVAILABLE", True)
    mocker.patch.dict(os.environ, {}, clear=True)

    # 2. ACT & 3. ASSERT
    with pytest.raises(ValueError, match="GOOGLE_API_KEY missing"):
        strategy.count("text", "gemini-1.5")


# ------------------------------------------------------------------------------
# SCENARIO: Model Normalization and Successful Counting
# ------------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize("input_model, expected_api_id", [
    ("Gemini 1.5 Flash", "gemini-1.5-flash"),
    ("models/gemini-1.5-pro", "gemini-1.5-pro"),
    ("gemini-2.0-experimental", "gemini-2.0-experimental"),
    ("custom-model-without-keyword", "gemini-1.5-flash"),
])
def test_should_normalize_model_ids_and_handle_fallbacks_correctly(
        mocker, mock_google_client, strategy, input_model, expected_api_id
):
    """Tests the string normalization logic required for Google API compatibility."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.google.GOOGLE_AVAILABLE", True)
    mocker.patch.dict(os.environ, {"GOOGLE_API_KEY": "AIza_test_key"})
    client_instance = mock_google_client

    # 2. ACT
    count = strategy.count("Hello Gemini", input_model)

    # 3. ASSERT
    assert count == 123
    client_instance.models.count_tokens.assert_called_once_with(
        model=expected_api_id,
        contents="Hello Gemini"
    )


# ------------------------------------------------------------------------------
# SCENARIO: Error Handling
# ------------------------------------------------------------------------------

@pytest.mark.unit
def test_should_log_and_propagate_google_api_errors(mocker, mock_google_client, strategy):
    """Ensures that remote SDK exceptions are captured in logs and re-raised."""
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.google.GOOGLE_AVAILABLE", True)
    mocker.patch.dict(os.environ, {"GOOGLE_API_KEY": "valid_key"})

    client_instance = mock_google_client
    client_instance.models.count_tokens.side_effect = Exception("Quota Exceeded")

    mock_logger = mocker.patch("transcriptor4ai.application.processing.strategies.google.logger.error")

    # 2. ACT & 3. ASSERT
    with pytest.raises(Exception, match="Quota Exceeded"):
        strategy.count("text", "gemini-1.5")

    # 3. ASSERT: Verification of technical logging
    mock_logger.assert_called_once()