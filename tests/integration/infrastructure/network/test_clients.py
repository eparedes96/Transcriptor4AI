# ==============================================================================
# TEST GROUP: NETWORK INFRASTRUCTURE CLIENTS (INTEGRATION)
# ==============================================================================


import pytest
import requests

from transcriptor4ai.infrastructure.network.github_release_client import GithubReleaseClient
from transcriptor4ai.infrastructure.network.pricing_api_client import PricingApiClient

# ------------------------------------------------------------------------------
# PRICING API CLIENT TESTS
# ------------------------------------------------------------------------------

@pytest.fixture
def pricing_client():
    return PricingApiClient()


@pytest.mark.integration
def test_pricing_client_fetch_success(pricing_client, mocker):
    """
    Verifies that the pricing client successfully fetches and parses
    the remote JSON model database.
    """
    # 1. ARRANGE
    mock_data = {"gpt-4o": {"input_cost_per_token": 0.000005}}
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = mock_data
    mock_response.content = b'{"gpt-4o": {"input_cost_per_token": 0.000005}}'

    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = pricing_client.fetch_external_model_data("http://fake-url.com")

    # 3. ASSERT
    assert result == mock_data
    requests.get.assert_called_once()


@pytest.mark.integration
def test_pricing_client_handles_timeout(pricing_client, mocker):
    """
    Ensures that a network timeout returns None instead of
    crashing the application start sequence.
    """
    # 1. ARRANGE
    mocker.patch("requests.get", side_effect=requests.exceptions.Timeout)

    # 2. ACT
    result = pricing_client.fetch_external_model_data("http://slow-url.com")

    # 3. ASSERT
    assert result is None


@pytest.mark.integration
@pytest.mark.parametrize("status_code", [404, 500])
def test_pricing_client_handles_http_errors(pricing_client, mocker, status_code):
    """
    Validates resilience against various HTTP failure codes.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = status_code
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError()
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = pricing_client.fetch_external_model_data("http://error-url.com")

    # 3. ASSERT
    assert result is None


# ------------------------------------------------------------------------------
# GITHUB RELEASE CLIENT TESTS
# ------------------------------------------------------------------------------

@pytest.fixture
def github_client():
    return GithubReleaseClient()


@pytest.mark.integration
def test_github_client_detects_newer_version(github_client, mocker):
    """
    Validates the version comparison logic: Remote v2.2.0 > Local v2.1.0.
    """
    # 1. ARRANGE
    mock_api_response = {
        "tag_name": "v2.2.0",
        "html_url": "https://github.com/release/2.2.0",
        "body": "New Features",
        "assets": [
            {"name": "transcriptor4ai.exe", "browser_download_url": "http://download.com/app.exe"}
        ]
    }
    mocker.patch("requests.get")
    requests.get.return_value.status_code = 200
    requests.get.return_value.json.return_value = mock_api_response

    # 2. ACT
    # Current local version is 2.1.0
    result = github_client.check_for_updates("2.1.0")

    # 3. ASSERT
    assert result["has_update"] is True
    assert result["latest_version"] == "2.2.0"
    assert result["binary_url"] == "http://download.com/app.exe"


@pytest.mark.integration
def test_github_client_download_binary_stream(github_client, mocker, tmp_path):
    """
    Verifies the buffered download logic (streaming chunks) and
    progress reporting callback.
    """
    # 1. ARRANGE: Set up staging environment and streaming mocks
    dest_path = str(tmp_path / "update.exe")
    mock_content = [b"chunk1", b"chunk2", b"chunk3"]

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-length": "18"}
    mock_response.iter_content.return_value = iter(mock_content)

    # Configure the mock to return itself when entering the context manager
    mock_response.__enter__.return_value = mock_response

    mocker.patch("requests.get", return_value=mock_response)

    progress_updates = []

    def progress_callback(p):
        progress_updates.append(p)

    # 2. ACT: Execute the binary download process
    success, msg = github_client.download_binary_stream(
        "http://fake.com/app.exe", dest_path, progress_callback
    )

    # 3. ASSERT: Verify physical side effects and callback telemetry
    assert success is True
    with open(dest_path, "rb") as f:
        # Ensures chunks were concatenated correctly on disk
        assert f.read() == b"chunk1chunk2chunk3"

    # Verify the callback was triggered and reached 100%
    assert len(progress_updates) > 0
    assert progress_updates[-1] == 100.0


@pytest.mark.integration
def test_github_client_fetch_checksum_success(github_client, mocker):
    """
    Validates that the client can parse a remote .sha256 sidecar file.
    """
    # 1. ARRANGE
    mock_sha_content = "54e9a3fff273ffed2552165e6fb679a4cc3e0c3badb22dafd62c7dac289d2ef4  app.exe"
    mocker.patch("requests.get")
    requests.get.return_value.status_code = 200
    requests.get.return_value.text = mock_sha_content

    result_dict = {}

    # 2. ACT
    github_client._fetch_checksum("http://fake.com/hash", {}, result_dict)

    # 3. ASSERT
    assert result_dict["sha256"] == "54e9a3fff273ffed2552165e6fb679a4cc3e0c3badb22dafd62c7dac289d2ef4"