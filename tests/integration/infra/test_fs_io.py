from __future__ import annotations

"""
Integration tests for FileSystem Infrastructure.

Validates path normalization, cross-platform data directory resolution,
and naming collision detection across different OS environments.
"""

import os
from pathlib import Path
from unittest.mock import patch

from transcriptor4ai.infra.fs import (
    check_existing_output_files,
    get_user_data_dir,
    normalize_path,
    safe_mkdir,
)

# -----------------------------------------------------------------------------
# PATH RESOLUTION TESTS
# -----------------------------------------------------------------------------

def test_get_user_data_dir_windows() -> None:
    """TC-01: Verify resolution of %LOCALAPPDATA% on Windows systems."""
    mock_appdata = "C:/Users/Test/AppData/Local"
    with patch("os.name", "nt"):
        with patch.dict(os.environ, {"LOCALAPPDATA": mock_appdata}):
            # We mock makedirs to avoid physical side effects during OS-spoofing
            with patch("os.makedirs"):
                path = get_user_data_dir()
                assert "Transcriptor4AI" in path
                assert path.lower().startswith(os.path.abspath(mock_appdata).lower())


def test_get_user_data_dir_unix() -> None:
    """TC-01: Verify resolution of ~/.transcriptor4ai on Unix-like systems."""
    mock_home = "/home/testuser"
    with patch("os.name", "posix"):
        with patch("os.path.expanduser", return_value=mock_home):
            with patch("os.makedirs"):
                path = get_user_data_dir()
                normalized_path = path.replace("\\", "/")
                assert normalized_path.endswith("/home/testuser/.transcriptor4ai")


def test_normalize_path_expansion() -> None:
    """TC-02: Verify expansion of environment variables and user shortcuts."""
    with patch.dict(os.environ, {"TEST_VAR": "my_folder"}):
        # Test env var expansion
        path = normalize_path("$TEST_VAR/sub", fallback=".")
        assert path.lower().endswith(os.path.join("my_folder", "sub").lower())

        # Test home expansion (~)
        with patch("os.path.expanduser", side_effect=lambda p: p.replace("~", "/home/user")):
            path = normalize_path("~/code", fallback=".")
            assert "code" in Path(path).parts


# -----------------------------------------------------------------------------
# FILESYSTEM OPERATIONS TESTS
# -----------------------------------------------------------------------------

def test_check_existing_output_files(tmp_path: Path) -> None:
    """TC-03: Verify detection of naming collisions in target directories."""
    # Setup: Create some existing files
    (tmp_path / "file1.txt").write_text("exists")
    (tmp_path / "file2.txt").write_text("exists")

    names_to_check = ["file1.txt", "file2.txt", "missing.txt"]
    existing = check_existing_output_files(str(tmp_path), names_to_check)

    assert len(existing) == 2
    assert any(e.endswith("file1.txt") for e in existing)
    assert any(e.endswith("file2.txt") for e in existing)
    assert not any(e.endswith("missing.txt") for e in existing)


def test_safe_mkdir_success(tmp_path: Path) -> None:
    """TC-04: Verify recursive directory creation."""
    target = tmp_path / "deep" / "nested" / "dir"
    success, err = safe_mkdir(str(target))

    assert success is True
    assert err is None
    assert target.exists()


def test_safe_mkdir_permission_error() -> None:
    """TC-04: Verify error handling when directory creation fails."""
    with patch("os.makedirs", side_effect=OSError("Permission Denied")):
        success, err = safe_mkdir("/root/forbidden")
        assert success is False
        assert "Permission Denied" in err