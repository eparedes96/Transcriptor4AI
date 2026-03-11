import pytest
import requests

from transcriptor4ai.infrastructure.network.telemetry_api_client import TelemetryApiClient

# ==============================================================================
# TEST GROUP: TELEMETRY CLIENT INTEGRITY
# ==============================================================================

@pytest.fixture
def client():
    """Provides a fresh instance of the TelemetryApiClient."""
    return TelemetryApiClient()

@pytest.fixture
def feedback_payload():
    """Returns a standard feedback structure for testing."""
    return {
        "type": "Bug Report",
        "subject": "UI Glitch",
        "message": "The button is misaligned",
        "version": "2.1.0"
    }

def test_submit_feedback_should_return_true_on_success(mocker, client, feedback_payload):
    """
    Happy Path: Verifies that a 200 response from Formspree results in a success status.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    m_post = mocker.patch("requests.post", return_value=mock_response)

    # 2. ACT
    success, message = client.submit_feedback(feedback_payload)

    # 3. ASSERT
    assert success is True
    assert message == "Success"
    # Ensures the endpoint and headers are correct
    m_post.assert_called_once()
    args, kwargs = m_post.call_args
    assert "formspree.io" in args[0]
    assert kwargs["json"] == feedback_payload
    assert "User-Agent" in kwargs["headers"]

def test_submit_error_report_should_handle_http_errors_gracefully(mocker, client):
    """
    Sad Path: If the server returns a 500 error, the client should return False
    without raising exceptions.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 500
    mocker.patch("requests.post", return_value=mock_response)
    report_data = {"error": "IndexError", "traceback": "..."}

    # 2. ACT
    success, message = client.submit_error_report(report_data)

    # 3. ASSERT
    assert success is False
    assert "HTTP 500" in message

def test_telemetry_should_be_resilient_to_network_timeouts(mocker, client, feedback_payload):
    """
    Critical Point: Ensures that a slow network doesn't block the UI infinitely.
    The client must catch the Timeout and return a failure state.
    """
    # 1. ARRANGE
    mocker.patch(
        "requests.post",
        side_effect=requests.exceptions.Timeout("Connection timed out")
    )

    # 2. ACT
    success, message = client.submit_feedback(feedback_payload)

    # 3. ASSERT
    assert success is False
    assert "timed out" in message.lower()

def test_telemetry_should_handle_connection_failures(mocker, client, feedback_payload):
    """
    Sad Path: Verifies behavior when there is no internet connection or DNS fails.
    """
    # 1. ARRANGE
    mocker.patch(
        "requests.post",
        side_effect=requests.exceptions.ConnectionError("Failed to resolve host")
    )

    # 2. ACT
    success, message = client.submit_feedback(feedback_payload)

    # 3. ASSERT
    assert success is False
    assert "failed" in message.lower()

@pytest.mark.parametrize("status_code", [200, 201])
def test_secure_post_internal_identifies_all_success_codes(mocker, client, status_code):
    """
    Validates that both 200 (OK) and 201 (Created) are treated as successful submissions.
    """
    # 1. ARRANGE
    mock_res = mocker.Mock()
    mock_res.status_code = status_code
    mocker.patch("requests.post", return_value=mock_res)

    # 2. ACT
    # Accessing private method for unit testing internal logic
    success, _ = client._secure_post("http://fake.url", {"data": "test"})

    # 3. ASSERT
    assert success is True

def test_secure_post_should_log_warning_on_failure(mocker, client):
    """
    Ensures that failed submissions are logged for developer diagnostic,
    even if the UI doesn't show a crash.
    """
    # 1. ARRANGE
    mock_res = mocker.Mock()
    mock_res.status_code = 403
    mocker.patch("requests.post", return_value=mock_res)
    mock_logger = mocker.patch("transcriptor4ai.infrastructure.network.telemetry_api_client.logger.warning")

    # 2. ACT
    client.submit_feedback({"test": "data"})

    # 3. ASSERT
    # Verification that the failure was logged
    mock_logger.assert_called_once()
    assert "403" in mock_logger.call_args[0][0]