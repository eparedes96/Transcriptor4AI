from __future__ import annotations

"""
Integration tests for Network Infrastructure.

Utilizes mocking to verify GitHub API update checks, binary streaming,
and telemetry submission without making real network calls.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

from transcriptor4ai.infra.network import (
    _calculate_sha256,
    check_for_updates,
    download_binary_stream,
    submit_feedback,
)

# -----------------------------------------------------------------------------
# UPDATE & DOWNLOAD TESTS
# -----------------------------------------------------------------------------

def test_check_for_updates_newer_version() -> None:
    """TC-01: Verify detection of a newer version from GitHub API."""
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "tag_name": "v9.9.9",
        "html_url": "https://github.com/test/release",
        "body": "New features",
        "assets": [
            {"name": "transcriptor4ai.exe", "browser_download_url": "https://host/app.exe"},
            {"name": "checksum.sha256", "browser_download_url": "https://host/hash"}
        ]
    }

    with patch("requests.get", return_value=mock_response):
        result = check_for_updates("1.0.0")

        assert result["has_update"] is True
        assert result["latest_version"] == "9.9.9"
        assert result["binary_url"] == "https://host/app.exe"


def test_download_binary_stream_success(tmp_path: Path) -> None:
    """TC-02: Verify buffered download of binary assets."""
    dest_path = tmp_path / "downloaded.exe"
    mock_content = [b"chunk1", b"chunk2", b"chunk3"]

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"content-length": "18"}
    mock_response.iter_content.return_value = iter(mock_content)
    mock_response.__enter__.return_value = mock_response

    with patch("requests.get", return_value=mock_response):
        progress_calls = []

        def callback(p: float) -> None:
            """Track progress updates without using lambda."""
            progress_calls.append(p)

        success, msg = download_binary_stream("https://host/app.exe", str(dest_path), callback)

        assert success is True
        assert dest_path.read_bytes() == b"chunk1chunk2chunk3"
        assert len(progress_calls) > 0
        assert progress_calls[-1] == 100.0


# -----------------------------------------------------------------------------
# TELEMETRY & INTEGRITY TESTS
# -----------------------------------------------------------------------------

def test_submit_feedback_success() -> None:
    """TC-04: Verify telemetry submission to Formspree endpoint."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch("requests.post", return_value=mock_response) as mock_post:
        payload = {"user": "test", "msg": "hello"}
        success, msg = submit_feedback(payload)

        assert success is True
        # Verify JSON transmission
        args, kwargs = mock_post.call_args
        assert kwargs["json"] == payload


def test_sha256_verification(tmp_path: Path) -> None:
    """TC-03: Verify local file integrity calculation."""
    f = tmp_path / "integrity.bin"
    f.write_bytes(b"data_to_hash")

    # Expected SHA256 for 'data_to_hash'
    expected = "54e9a3fff273ffed2552165e6fb679a4cc3e0c3badb22dafd62c7dac289d2ef4"

    actual = _calculate_sha256(str(f))
    assert actual == expected