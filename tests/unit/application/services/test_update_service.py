import pytest

from transcriptor4ai.application.services.update_service import UpdateManager, UpdateStatus
from transcriptor4ai.domain.ports.network_port import IUpdateClient
from transcriptor4ai.domain.ports.system_port import IFileSystem

# ==============================================================================
# TEST GROUP: UPDATE LIFECYCLE MANAGEMENT
# ==============================================================================

@pytest.fixture
def update_context(mocker):
    """
    Sets up the UpdateManager with mocked ports and utility functions.
    """
    mock_network = mocker.Mock(spec=IUpdateClient)
    mock_fs = mocker.Mock(spec=IFileSystem)

    # Mock internal hashing utility used by the manager
    mock_hash = mocker.patch("transcriptor4ai.shared.hashing.calculate_sha256")

    # Standard setup for temp directories
    mock_fs.get_user_data_dir.return_value = "/app/data"

    manager = UpdateManager(mock_network, mock_fs)
    return manager, mock_network, mock_fs, mock_hash


@pytest.mark.unit
def test_should_reach_ready_when_update_is_valid_exe(update_context):
    """
    Validates the full cycle for a standard .exe update.
    """
    # 1. ARRANGE
    manager, mock_net, mock_fs, mock_hash = update_context
    current_ver = "1.0.0"
    latest_ver = "1.1.0"
    target_url = "http://api.com/v1.1.0.exe"
    expected_sha = "valid_sha256"

    mock_net.check_for_updates.return_value = {
        "has_update": True,
        "latest_version": latest_ver,
        "binary_url": target_url,
        "sha256": expected_sha
    }
    mock_net.download_binary_stream.return_value = (True, "Success")
    mock_hash.return_value = expected_sha  # Integrity check passed

    # 2. ACT
    manager.run_silent_cycle(current_ver)

    # 3. ASSERT
    assert manager.status == UpdateStatus.READY
    assert manager.update_info["latest_version"] == latest_ver
    assert manager.pending_path.endswith(".exe")
    mock_fs.unpack_executable_from_zip.assert_not_called()


@pytest.mark.unit
def test_should_unpack_and_delete_zip_when_update_is_compressed(update_context):
    """
    Ensures that ZIP updates are correctly extracted and the archive is cleaned up.
    """
    # 1. ARRANGE
    manager, mock_net, mock_fs, mock_hash = update_context
    mock_net.check_for_updates.return_value = {
        "has_update": True,
        "latest_version": "2.0.0",
        "binary_url": "http://api.com/update.zip",
        "sha256": "sha_zip"
    }
    mock_net.download_binary_stream.return_value = (True, "Downloaded")
    mock_hash.return_value = "sha_zip"
    mock_fs.unpack_executable_from_zip.return_value = "/app/data/updates/transcriptor.exe"

    # 2. ACT
    manager.run_silent_cycle("1.0.0")

    # 3. ASSERT
    assert manager.status == UpdateStatus.READY
    assert manager.pending_path == "/app/data/updates/transcriptor.exe"
    # Logic verification: Must extract AND then delete the zip
    mock_fs.unpack_executable_from_zip.assert_called_once()
    mock_fs.delete_file.assert_called_once()


@pytest.mark.unit
def test_should_set_error_status_on_checksum_mismatch(update_context):
    """
    Security Test: If the downloaded file's hash doesn't match the API info,
    the manager must abort and set ERROR status.
    """
    # 1. ARRANGE
    manager, mock_net, _, mock_hash = update_context
    mock_net.check_for_updates.return_value = {
        "has_update": True,
        "binary_url": "http://api.com/hacked.exe",
        "sha256": "legit_hash"
    }
    mock_net.download_binary_stream.return_value = (True, "Success")
    mock_hash.return_value = "corrupted_or_malicious_hash"

    # 2. ACT
    manager.run_silent_cycle("1.0.0")

    # 3. ASSERT
    assert manager.status == UpdateStatus.ERROR
    assert manager.pending_path == ""  # No path should be exposed on error


@pytest.mark.unit
def test_should_stay_idle_if_no_new_version_available(update_context):
    """
    Verifies that if the client reports no updates, the manager does nothing.
    """
    # 1. ARRANGE
    manager, mock_net, mock_fs, _ = update_context
    mock_net.check_for_updates.return_value = {"has_update": False}

    # 2. ACT
    manager.run_silent_cycle("1.0.0")

    # 3. ASSERT
    assert manager.status == UpdateStatus.IDLE
    mock_net.download_binary_stream.assert_not_called()
    mock_fs.safe_mkdir.assert_called_once()  # Should still prepare temp dir


@pytest.mark.unit
@pytest.mark.parametrize("fail_stage", ["check", "download"])
def test_should_handle_network_exceptions_gracefully(update_context, fail_stage):
    """
    Resilience Test: Ensures that network timeouts or connection drops
    don't crash the manager.
    """
    # 1. ARRANGE
    manager, mock_net, _, _ = update_context

    if fail_stage == "check":
        mock_net.check_for_updates.side_effect = Exception("DNS Failure")
    else:
        mock_net.check_for_updates.return_value = {"has_update": True, "binary_url": "..."}
        mock_net.download_binary_stream.return_value = (False, "Timeout during download")

    # 2. ACT
    manager.run_silent_cycle("1.0.0")

    # 3. ASSERT
    assert manager.status == UpdateStatus.ERROR


@pytest.mark.unit
def test_should_handle_corrupted_zip_extraction_failure(update_context):
    """
    Verifies that if the extraction fails (e.g. invalid zip), status is ERROR.
    """
    # 1. ARRANGE
    manager, mock_net, mock_fs, mock_hash = update_context
    mock_net.check_for_updates.return_value = {
        "has_update": True,
        "binary_url": "http://api.com/bad.zip",
        "sha256": "abc"
    }
    mock_net.download_binary_stream.return_value = (True, "OK")
    mock_hash.return_value = "abc"

    # Mock unpacking failure (returns None according to IFileSystem port)
    mock_fs.unpack_executable_from_zip.return_value = None

    # 2. ACT
    manager.run_silent_cycle("1.0.0")

    # 3. ASSERT
    assert manager.status == UpdateStatus.ERROR