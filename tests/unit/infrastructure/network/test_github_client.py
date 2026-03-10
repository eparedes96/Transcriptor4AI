import pytest
import requests
from io import BytesIO
from transcriptor4ai.infrastructure.network.github_release_client import GithubReleaseClient


# ==============================================================================
# TEST GROUP: GITHUB RELEASE CLIENT (UPDATE DISCOVERY)
# ==============================================================================

@pytest.fixture
def client():
    """Provides a fresh GithubReleaseClient instance."""
    return GithubReleaseClient()


def test_check_for_updates_should_detect_new_version(mocker, client):
    """
    Happy Path: Verifies that the client identifies a newer version and
    extracts the correct asset URLs.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tag_name": "v3.0.0",
        "html_url": "https://github.com/releases/3.0.0",
        "body": "Amazing new features",
        "assets": [
            {"name": "transcriptor_v3.exe", "browser_download_url": "https://api.com/v3.exe"},
            {"name": "hashes.sha256", "browser_download_url": "https://api.com/v3.sha256"}
        ]
    }
    m_get = mocker.patch("requests.get", return_value=mock_response)

    # Mocking the internal checksum fetch to avoid a second network call
    m_checksum = mocker.patch.object(client, "_fetch_checksum")

    # 2. ACT
    result = client.check_for_updates(current_version="2.1.0")

    # 3. ASSERT
    assert result["has_update"] is True
    assert result["latest_version"] == "3.0.0"
    assert result["binary_url"] == "https://api.com/v3.exe"
    assert "Amazing new features" in result["changelog"]
    assert m_get.called


def test_check_for_updates_should_ignore_older_or_equal_versions(mocker, client):
    """
    Ensures that if the remote version is older or equal, no update is signaled.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"tag_name": "v2.1.0"}
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    result = client.check_for_updates(current_version="2.1.0")

    # 3. ASSERT
    assert result["has_update"] is False
    assert result["latest_version"] == "2.1.0"


def test_check_for_updates_should_handle_api_errors_gracefully(mocker, client):
    """
    Sad Path: If GitHub API returns 404 or fails, the client should
    report the error instead of crashing.
    """
    # 1. ARRANGE
    mocker.patch("requests.get", side_effect=requests.exceptions.RequestException("API Down"))

    # 2. ACT
    result = client.check_for_updates(current_version="2.1.0")

    # 3. ASSERT
    assert result["has_update"] is False
    assert "API Down" in result["error"]


# ==============================================================================
# TEST GROUP: BINARY ACQUISITION (STREAMING)
# ==============================================================================

def test_download_binary_stream_success(mocker, client, tmp_path):
    """
    Verifies that the download logic processes content in chunks and
    reports progress accurately.
    """
    # 1. ARRANGE
    dest_path = tmp_path / "update.exe"
    mock_content = [b"chunk1_", b"chunk2_", b"chunk3"]  # Total 18 bytes

    mock_response = mocker.MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {'content-length': '21'}
    mock_response.iter_content.return_value = iter(mock_content)
    mock_response.__enter__.return_value = mock_response  # Support context manager

    mocker.patch("requests.get", return_value=mock_response)

    progress_calls = []

    def progress_cb(percent): progress_calls.append(percent)

    # 2. ACT
    success, msg = client.download_binary_stream(
        "https://api.com/file.exe", str(dest_path), progress_callback=progress_cb
    )

    # 3. ASSERT
    assert success is True
    assert dest_path.exists()
    assert dest_path.read_bytes() == b"chunk1_chunk2_chunk3"
    # Verify that progress was reported (should have called it for each chunk)
    assert len(progress_calls) > 0
    assert progress_calls[-1] == pytest.approx(100.0)


def test_download_binary_stream_handles_http_failure(mocker, client, tmp_path):
    """
    Ensures that if the download server returns 404, it reports failure.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Not Found")
    mock_response.__enter__.return_value = mock_response
    mocker.patch("requests.get", return_value=mock_response)

    # 2. ACT
    success, msg = client.download_binary_stream("http://bad.url", str(tmp_path / "fail.exe"))

    # 3. ASSERT
    assert success is False
    assert "Not Found" in msg


# ==============================================================================
# TEST GROUP: CHECKSUM FETCHING (INTERNAL UTILS)
# ==============================================================================

def test_fetch_checksum_should_extract_hex_string(mocker, client):
    """
    Validates that the helper can parse a standard .sha256 file content.
    """
    # 1. ARRANGE
    mock_response = mocker.Mock()
    mock_response.status_code = 200
    # Common format: "hash filename" or just "hash"
    mock_response.text = "54e9a3fff273ffed2552165e6fb679a4cc3e0c3badb22dafd62c7dac289d2ef4  binary.exe"
    mocker.patch("requests.get", return_value=mock_response)

    result_dict = {}

    # 2. ACT
    client._fetch_checksum("http://url.sha256", {}, result_dict)

    # 3. ASSERT
    assert result_dict["sha256"] == "54e9a3fff273ffed2552165e6fb679a4cc3e0c3badb22dafd62c7dac289d2ef4"


def test_fetch_checksum_should_fail_silently_on_error(mocker, client):
    """
    Checksum failure shouldn't abort the update process, just leave sha256 as None.
    """
    # 1. ARRANGE
    mocker.patch("requests.get", side_effect=Exception("Network Timeout"))
    result_dict = {"sha256": None}

    # 2. ACT
    client._fetch_checksum("http://url.sha256", {}, result_dict)

    # 3. ASSERT
    assert result_dict["sha256"] is None  # Remains unchanged