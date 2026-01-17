from __future__ import annotations

"""
Unit tests for the Update Management Service.

Verifies the lifecycle of background updates: state transitions,
directory preparation, and cryptographic verification of downloaded binaries.
"""

import os
import shutil
from unittest.mock import MagicMock, patch
import pytest

from transcriptor4ai.core.services.updater import UpdateManager, UpdateStatus


@pytest.fixture
def updater() -> UpdateManager:
    """Initialize a fresh UpdateManager instance."""
    return UpdateManager()


def test_updater_initial_state(updater: UpdateManager) -> None:
    """TC-01: Verify that the manager starts in IDLE state."""
    assert updater.status == UpdateStatus.IDLE
    assert updater.pending_path == ""


@patch("transcriptor4ai.core.services.updater.network.check_for_updates")
def test_run_silent_cycle_no_update(mock_check: MagicMock, updater: UpdateManager) -> None:
    """TC-02: Verify state returns to IDLE if no update is available."""
    mock_check.return_value = {"has_update": False}

    updater.run_silent_cycle("1.0.0")

    assert updater.status == UpdateStatus.IDLE


@patch("transcriptor4ai.core.services.updater.network.check_for_updates")
@patch("transcriptor4ai.core.services.updater.network.download_binary_stream")
@patch("transcriptor4ai.core.services.updater.network._calculate_sha256")
def test_run_silent_cycle_success(
        mock_hash: MagicMock,
        mock_download: MagicMock,
        mock_check: MagicMock,
        updater: UpdateManager,
        tmp_path: pytest.TempPathFactory
) -> None:
    """TC-03: Verify successful update flow with checksum verification."""
    # Setup mocks
    mock_check.return_value = {
        "has_update": True,
        "latest_version": "2.0.0",
        "binary_url": "http://example.com/app.exe",
        "sha256": "correct_hash"
    }
    mock_download.return_value = (True, "Success")
    mock_hash.return_value = "correct_hash"

    # Execute
    with patch("transcriptor4ai.core.services.updater.get_user_data_dir", return_value=str(tmp_path)):
        # Re-init to use the mock temp dir
        updater._temp_dir = os.path.join(str(tmp_path), "updates")
        updater.run_silent_cycle("1.0.0")

    assert updater.status == UpdateStatus.READY
    assert "transcriptor4ai_v2.0.0.exe" in updater.pending_path


@patch("transcriptor4ai.core.services.updater.network.check_for_updates")
@patch("transcriptor4ai.core.services.updater.network.download_binary_stream")
@patch("transcriptor4ai.core.services.updater.network._calculate_sha256")
def test_run_silent_cycle_integrity_failure(
        mock_hash: MagicMock,
        mock_download: MagicMock,
        mock_check: MagicMock,
        updater: UpdateManager,
        tmp_path: pytest.TempPathFactory
) -> None:
    """TC-04: Verify that a checksum mismatch leads to an ERROR state."""
    mock_check.return_value = {
        "has_update": True,
        "latest_version": "2.0.0",
        "binary_url": "http://example.com/app.exe",
        "sha256": "expected_hash"
    }
    mock_download.return_value = (True, "Success")
    mock_hash.return_value = "wrong_hash"

    with patch("transcriptor4ai.core.services.updater.get_user_data_dir", return_value=str(tmp_path)):
        updater._temp_dir = os.path.join(str(tmp_path), "updates")
        updater.run_silent_cycle("1.0.0")

    assert updater.status == UpdateStatus.ERROR