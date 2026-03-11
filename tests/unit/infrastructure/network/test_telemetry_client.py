import pytest
import requests

from transcriptor4ai.infrastructure.network.pricing_api_client import (
    MODEL_DATA_TIMEOUT,
    PricingApiClient,
)

# ==============================================================================
# TEST GROUP: PRICING API CLIENT (DYNAMIC DISCOVERY)
# ==============================================================================

@pytest.fixture
def client():
    """Provides a fresh instance of the PricingApiClient."""
    return PricingApiClient()


def test_fetch_external_model_data_success(mocker, client):
    """
    Happy Path: Verifies that valid JSON from a remote source is
    correctly parsed into a dictionary.
    """
    # 1. ARRANGE
    mock_data = {
        "gpt-4o": {"input_cost_per_token": 0.000005},
        "claude-3-5-sonnet": {"input_cost_per_token": 0.000003}
    }
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_response.content = b'{"mock": "data"}'  # Used for size logging

    m_get = mocker.patch("requests.get", return_value=mock_response)
    test_url = "https://api.test/models.json"

    # 2. ACT
    result = client.fetch_external_model_data(test_url)

    # 3. ASSERT
    assert result == mock_data
    assert isinstance(result, dict)
    m_get.assert_called_once_with(
        test_url,
        headers=mocker.ANY,
        timeout=MODEL_DATA_TIMEOUT
    )


def test_fetch_external_model_data_should_return_none_on_http_error(mocker, client):
    """
    Sad Path: Verifies that HTTP errors (e.g., 404, 500) do not raise
    exceptions but return None for fallback triggering.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = client.fetch_external_model_data("http://bad-url.com")

    # 3. ASSERT
    # Ensures the client handles failure gracefully
    assert result is None


def test_fetch_external_model_data_should_handle_timeout_gracefully(mocker, client):
    """
    Critical Point: Verifies that network timeouts are caught to
    prevent UI/Bootstrap hanging.
    """
    # 1. ARRANGE
    mocker.patch(
        "requests.get",
        side_effect=requests.exceptions.Timeout("Operation timed out")
    )
    mock_logger = mocker.patch("transcriptor4ai.infrastructure.network.pricing_api_client.logger.warning")

    # 2. ACT
    result = client.fetch_external_model_data("http://slow-url.com")

    # 3. ASSERT
    assert result is None
    # Verify the user/dev is informed about the timeout fallback
    mock_logger.assert_called()
    assert "timed out" in mock_logger.call_args[0][0].lower()


def test_fetch_external_model_data_should_reject_invalid_json_root(mocker, client):
    """
    Edge Case: LiteLLM schema expects a Dict. If the API returns a List
    or primitive, it should be treated as malformed.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    # Returning a list instead of a dict
    mock_response.json.return_value = ["model1", "model2"]
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = client.fetch_external_model_data("http://malformed-api.com")

    # 3. ASSERT
    assert result is None


def test_fetch_external_model_data_should_be_resilient_to_parsing_errors(mocker, client):
    """
    Ensures that if the response is not valid JSON, the client
    doesn't crash the application.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    # Simulate JSON decoding failure
    mock_response.json.side_effect = ValueError("No JSON object could be decoded")
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = client.fetch_external_model_data("http://invalid-json.com")

    # 3. ASSERT
    assert result is None


def test_fetch_external_model_data_includes_correct_user_agent(mocker, client):
    """
    Validation: Ensures a custom User-Agent is present to satisfy
    GitHub/Cloudflare security requirements.
    """
    # 1. ARRANGE
    m_get = mocker.patch("requests.get")
    m_get.return_value.status_code = 200
    m_get.return_value.json.return_value = {}

    # 2. ACT
    client.fetch_external_model_data("http://any.url")

    # 3. ASSERT
    args, kwargs = m_get.call_args
    headers = kwargs.get("headers", {})
    assert "User-Agent" in headers
    assert "Transcriptor4AI" in headers["User-Agent"]