from __future__ import annotations

"""
Integration tests for Network Model Discovery synchronization.

Validates HTTP communication, strict timeout enforcement, and 
handling of malformed remote JSON resources.
"""

from unittest.mock import MagicMock, patch

import requests

from transcriptor4ai.infra.network import fetch_external_model_data


def test_fetch_external_model_data_success() -> None:
    """TC-01: Verify successful retrieval and parsing of remote model JSON."""
    mock_data = {"Model-A": {"input_cost_per_token": 0.00001}}
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_data
    mock_resp.content = b"fake-content"

    with patch("requests.get", return_value=mock_resp) as mock_get:
        result = fetch_external_model_data("http://fake.url/models.json")

        assert result == mock_data
        mock_get.assert_called_once()
        # Verify user agent and timeout (NFR: 5s for discovery)
        args, kwargs = mock_get.call_args
        assert kwargs["timeout"] == 5
        assert "Transcriptor4AI" in kwargs["headers"]["User-Agent"]


def test_fetch_external_model_data_timeout() -> None:
    """TC-02: Verify that the function respects the strict 5s timeout."""
    with patch("requests.get", side_effect=requests.exceptions.Timeout):
        result = fetch_external_model_data("http://slow.url")
        assert result is None


def test_fetch_external_model_data_http_error() -> None:
    """TC-03: Verify handling of 404 or 500 HTTP errors."""
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError()

    with patch("requests.get", return_value=mock_resp):
        result = fetch_external_model_data("http://missing.url")
        assert result is None


def test_fetch_external_model_data_malformed_json() -> None:
    """TC-04: Verify resilience when the remote source returns invalid JSON."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    # Returns a list instead of expected dict
    mock_resp.json.return_value = ["not", "a", "dict"]

    with patch("requests.get", return_value=mock_resp):
        result = fetch_external_model_data("http://broken.url")
        assert result is None