from __future__ import annotations

import os
import pytest
from unittest.mock import MagicMock

from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

# ==============================================================================
# TEST GROUP: FILESYSTEM PERMISSIONS AND IO FAILURES
# ==============================================================================

@pytest.fixture
def fs() -> FileSystemAdapter:
    """Provides a fresh instance of the FileSystemAdapter."""
    return FileSystemAdapter()

@pytest.mark.integration
def test_safe_mkdir_returns_false_on_permission_error(fs, mocker):
    """
    Ensures that attempting to create a directory in a restricted location
    is caught gracefully and returns a failure tuple instead of raising OSError.
    """
    # 1. ARRANGE: Mock the OS level to raise a permission error
    mocker.patch(
        "transcriptor4ai.infrastructure.system.fs.io_manager.os.makedirs",
        side_effect=PermissionError("Access is denied")
    )

    # 2. ACT: Attempt to create a directory
    success, error_msg = fs.safe_mkdir("/system/root/protected_dir")

    # 3. ASSERT: Method caught the error
    assert success is False
    assert error_msg is not None
    assert "Access is denied" in error_msg

@pytest.mark.integration
def test_delete_file_returns_false_on_locked_file(fs, mocker):
    """
    Validates that trying to delete a file that is locked by another process
    or read-only results in a safe boolean False.
    """
    # 1. ARRANGE: Mock exists to True, then mock remove to fail
    mocker.patch(
        "transcriptor4ai.infrastructure.system.fs.io_manager.os.path.exists",
        return_value=True
    )
    mocker.patch(
        "transcriptor4ai.infrastructure.system.fs.io_manager.os.remove",
        side_effect=PermissionError("The process cannot access the file")
    )

    # 2. ACT: Attempt to delete
    result = fs.delete_file("/path/to/locked_file.txt")

    # 3. ASSERT: Failure was handled silently
    assert result is False

@pytest.mark.integration
def test_move_file_returns_false_on_access_denied(fs, mocker):
    """
    Ensures that atomic move operations that fail due to permissions
    or cross-device link issues are gracefully caught.
    """
    # 1. ARRANGE: Mock shutil.move to simulate failure
    mocker.patch(
        "transcriptor4ai.infrastructure.system.fs.io_manager.shutil.move",
        side_effect=OSError("Invalid cross-device link or permission denied")
    )

    # 2. ACT: Attempt to move
    result = fs.move_file("/tmp/staging.txt", "/protected/final.txt")

    # 3. ASSERT: Handled safely
    assert result is False

@pytest.mark.integration
def test_generate_unified_file_handles_read_only_destination(fs, mocker):
    """
    Verifies that the complex aggregation logic does not crash if the
    destination file cannot be opened for writing.
    """
    # 1. ARRANGE: Mock builtins.open to simulate a write-protected directory
    mocker.patch(
        "builtins.open",
        side_effect=PermissionError("Read-only file system")
    )

    category_paths = {"modules": "/tmp/stg_modules.txt"}

    # 2. ACT: Run the aggregation
    result = fs.generate_unified_file(
        output_path="/protected_drive/master.txt",
        base_path="/src",
        tree_path=None,
        category_paths=category_paths
    )

    # 3. ASSERT: Handled gracefully, returning False to the assembler
    assert result is False

@pytest.mark.integration
def test_write_text_file_propagates_os_error_by_design(fs, mocker):
    """
    Validates that low-level atomic write functions propagate the OSError.
    This is intended behavior so the worker thread can capture and report
    the exact file that failed.
    """
    # 1. ARRANGE: Mock builtins.open
    mocker.patch(
        "builtins.open",
        side_effect=PermissionError("Cannot open for writing")
    )

    # 2. ACT & ASSERT: The exception must bubble up
    with pytest.raises(PermissionError, match="Cannot open for writing"):
        fs.write_text_file("/restricted/output.txt", "Some content")