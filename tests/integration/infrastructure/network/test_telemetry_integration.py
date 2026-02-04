from __future__ import annotations

import pytest
import requests
from transcriptor4ai.infrastructure.network.telemetry_api_client import TelemetryApiClient


# ==============================================================================
# TEST GROUP: TELEMETRY API CLIENT INTEGRATION
# ==============================================================================

@pytest.fixture
def telemetry_client() -> TelemetryApiClient:
    """Provides a fresh instance of the TelemetryApiClient."""
    return TelemetryApiClient()


@pytest.fixture
def sample_payload() -> dict:
    """Provides a standard diagnostic payload for testing."""
    return {
        "type": "Bug Report",
        "subject": "Test Issue",
        "message": "This is a unit test message",
        "version": "2.1.0"
    }


@pytest.mark.integration
def test_submit_feedback_should_return_success_on_200_response(mocker, telemetry_client, sample_payload):
    """
    Verifies that a successful HTTP response (200/201) from the endpoint
    is correctly translated into a success status by the client.
    """
    # 1. ARRANGE: Mock requests.post to return a successful response
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mocker.patch("requests.post", return_value=mock_response)

    # 2. ACT: Execute the submission
    success, message = telemetry_client.submit_feedback(sample_payload)

    # 3. ASSERT: Verify the outcome and internal call parameters
    assert success is True
    assert message == "Success"
    requests.post.assert_called_once()

    # Ensure User-Agent and JSON headers are sent correctly
    args, kwargs = requests.post.call_args
    assert "User-Agent" in kwargs["headers"]
    assert kwargs["json"] == sample_payload


@pytest.mark.integration
@pytest.mark.parametrize("status_code", [400, 404, 500])
def test_submit_error_report_should_return_false_on_http_errors(mocker, telemetry_client, sample_payload, status_code):
    """
    Ensures that non-success HTTP status codes result in a failure status
    without raising unhandled exceptions.
    """
    # 1. ARRANGE: Mock requests.post with specific error codes
    mock_response = mocker.Mock()
    mock_response.status_code = status_code
    mocker.patch("requests.post", return_value=mock_response)

    # 2. ACT: Execute the submission
    success, message = telemetry_client.submit_error_report(sample_payload)

    # 3. ASSERT: Client should report failure
    assert success is False
    assert f"HTTP {status_code}" in message


@pytest.mark.integration
def test_telemetry_should_handle_request_timeout_gracefully(mocker, telemetry_client, sample_payload):
    """
    Verifies that network timeouts are caught by the client, returning
    a failure status instead of crashing the application.
    """
    # 1. ARRANGE: Simulate a timeout exception during the post request
    mocker.patch("requests.post", side_effect=requests.exceptions.Timeout("Connection timed out"))

    # 2. ACT: Execute the behavior
    success, message = telemetry_client.submit_feedback(sample_payload)

    # 3. ASSERT: Operation fails but is handled
    assert success is False
    assert "Connection timed out" in message


@pytest.mark.integration
def test_telemetry_should_handle_connection_failure(mocker, telemetry_client, sample_payload):
    """
    Ensures that physical connection issues (DNS, Socket) are caught and reported.
    """
    # 1. ARRANGE: Simulate a connection error
    mocker.patch("requests.post", side_effect=requests.exceptions.ConnectionError("Failed to connect"))

    # 2. ACT: Execute the behavior
    success, message = telemetry_client.submit_error_report(sample_payload)

    # 3. ASSERT: Returns false with error details
    assert success is False
    assert "Failed to connect" in message


@pytest.mark.integration
def test_secure_post_internal_logic_is_private_but_reachable_via_public_api(mocker, telemetry_client, sample_payload):
    """
    Validates that the specific endpoint URL is correctly targeted.
    """
    # 1. ARRANGE
    mock_post = mocker.patch("requests.post")
    mock_post.return_value.status_code = 200

    # 2. ACT
    telemetry_client.submit_feedback(sample_payload)

    # 3. ASSERT: Check if the hardcoded Formspree URL was used
    call_url = mock_post.call_args[0][0]
    assert "formspree.io" in call_url
    assert "/f/" in call_url