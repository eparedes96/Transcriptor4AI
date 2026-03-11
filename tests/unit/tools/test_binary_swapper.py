import pytest

from tools.sidecar import binary_swapper

# ==============================================================================
# TEST GROUP: PROCESS SYNCHRONIZATION (wait_for_pid)
# ==============================================================================

@pytest.mark.unit
def test_wait_for_pid_should_return_true_when_process_is_gone(mocker):
    """Verifies that the swapper detects when the parent process exits."""
    # 1. ARRANGE
    # Mock os.kill to raise OSError (Process not found) on second call
    mock_kill = mocker.patch("os.kill", side_effect=[None, OSError("No such process")])
    mocker.patch("time.sleep")  # Prevent actual waiting

    # 2. ACT
    result = binary_swapper.wait_for_pid(pid=1234, timeout=5)

    # 3. ASSERT
    assert result is True
    assert mock_kill.call_count == 2


@pytest.mark.unit
def test_wait_for_pid_should_return_false_on_timeout(mocker):
    """Ensures the script gives up if the process doesn't close within timeout."""
    # 1. ARRANGE
    mocker.patch("os.kill", return_value=None)  # Process always alive
    mocker.patch("time.sleep")

    # CRITICAL FIX: The logging system consumes time.time() for timestamps.
    # We provide extra values to satisfy logger calls + logic calls.
    mocker.patch("time.time", side_effect=[0, 0, 0, 10, 10, 10])

    # 2. ACT
    result = binary_swapper.wait_for_pid(pid=1234, timeout=5)

    # 3. ASSERT
    assert result is False


# ==============================================================================
# TEST GROUP: FILE SYSTEM ATOMICITY (_retry_rename)
# ==============================================================================

@pytest.mark.unit
def test_retry_rename_should_succeed_after_retries(mocker):
    """Simulates a locked file (common on Windows) that becomes free after reattempts."""
    # 1. ARRANGE
    mocker.patch("time.sleep")
    mocker.patch("os.path.exists", return_value=False)
    # Fails twice, succeeds on the third attempt
    mock_rename = mocker.patch("os.rename", side_effect=[OSError("Access Denied"), OSError("Locked"), None])

    # 2. ACT
    binary_swapper._retry_rename("src.exe", "dst.exe", max_retries=5)

    # 3. ASSERT
    assert mock_rename.call_count == 3


# ==============================================================================
# TEST GROUP: CORE UPDATE LIFECYCLE (run_update)
# ==============================================================================

@pytest.mark.unit
def test_run_update_integrity_check_failure_should_exit(mocker):
    """Security check: Abort if the new binary doesn't match the expected hash."""
    # 1. ARRANGE
    mocker.patch("tools.sidecar.binary_swapper.wait_for_pid", return_value=True)
    mocker.patch("tools.sidecar.binary_swapper.calculate_sha256", return_value="WRONG_HASH")
    mock_exit = mocker.patch("sys.exit")

    # 2. ACT
    binary_swapper.run_update("old.exe", "new.exe", 1234, expected_sha256="VALID_HASH")

    # 3. ASSERT
    mock_exit.assert_called_with(1)


@pytest.mark.unit
def test_run_update_full_successful_cycle(mocker, tmp_path):
    """Tests the happy path: Backup -> Replace -> Cleanup -> Restart."""
    # 1. ARRANGE
    old_exe = str(tmp_path / "app.exe")
    new_exe = str(tmp_path / "new.exe")

    mocker.patch("tools.sidecar.binary_swapper.wait_for_pid", return_value=True)
    mocker.patch("os.path.exists", return_value=True)
    mock_rename = mocker.patch("tools.sidecar.binary_swapper._retry_rename")
    mock_remove = mocker.patch("os.remove")
    mock_restart = mocker.patch("subprocess.Popen")

    # CRITICAL FIX: Store reference to the mock to verify it later correctly
    mock_startfile = mocker.patch("os.startfile", create=True)
    mocker.patch("time.sleep")

    # 2. ACT
    binary_swapper.run_update(old_exe, new_exe, pid=1234)

    # 3. ASSERT
    # Expect rename from old to backup (.old)
    mock_rename.assert_any_call(old_exe, old_exe + ".old")
    # Expect rename from new to old path
    mock_rename.assert_any_call(new_exe, old_exe)
    # Expect cleanup of backup
    mock_remove.assert_called_with(old_exe + ".old")
    # Verify restart attempt using the stored mock references
    assert mock_restart.called or mock_startfile.called


@pytest.mark.unit
def test_run_update_rollback_on_failure(mocker):
    """Verify that if deploying the new binary fails, the original is restored."""
    # 1. ARRANGE
    old = "app.exe"
    new = "new.exe"
    backup = old + ".old"

    mocker.patch("tools.sidecar.binary_swapper.wait_for_pid", return_value=True)
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("time.sleep")

    # First rename (backup) succeeds, second rename (deploy) fails, third (rollback) succeeds
    mock_rename = mocker.patch("tools.sidecar.binary_swapper._retry_rename",
                               side_effect=[None, RuntimeError("Disk Error"), None])

    # 2. ACT
    with pytest.raises(SystemExit):
        binary_swapper.run_update(old, new, pid=1234)

    # 3. ASSERT
    # The third call to retry_rename should be the rollback (backup -> old)
    mock_rename.assert_any_call(backup, old)