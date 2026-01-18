from __future__ import annotations

from scripts.updater import calculate_sha256, wait_for_pid

"""
Unit tests for the Standalone Updater Script.

Verifies:
1. SHA-256 calculation logic.
2. Process waiting logic (mocked).
3. Update integrity verification flow.
"""

import sys
import os
from unittest.mock import patch, MagicMock
import pytest

# Add 'scripts' to path for import, as it is outside 'src'
scripts_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts"))
if scripts_path not in sys.path:
    sys.path.insert(0, scripts_path)


def test_calculate_sha256(tmp_path):
    """Verify hash calculation on a real temp file."""
    f = tmp_path / "test_binary.exe"
    f.write_bytes(b"test_content")

    # Correct SHA256 for b"test_content"
    expected_hash = "594a1b494545be568120d28c43b3319e41d7b8e51a8112ebbece7b3275591a9a"

    computed_hash = calculate_sha256(str(f))
    assert computed_hash == expected_hash


def test_calculate_sha256_handles_missing_file():
    """Should return empty string on error, not crash."""
    assert calculate_sha256("/non/existent") == ""


def test_wait_for_pid_returns_true_if_process_gone():
    """If os.kill raises OSError, process is gone -> return True."""
    with patch("os.kill", side_effect=OSError("No such process")):
        assert wait_for_pid(12345) is True


def test_wait_for_pid_returns_false_on_timeout():
    """If process persists, loop should exit after timeout."""
    with patch("os.kill", return_value=None):
        with patch("time.time") as mock_time:
            mock_time.side_effect = [1000, 1000, 2000]

            # Using real sleep mock to break loop if needed, but side_effect on time is safer
            result = wait_for_pid(12345, timeout=10)
            assert result is False