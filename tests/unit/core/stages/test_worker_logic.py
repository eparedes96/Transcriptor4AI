from __future__ import annotations

"""
Unit tests for the Atomic Worker Logic.

Verifies the decision-making process of `process_file_task`:
1. File classification (Module vs Test vs Resource).
2. Skipping logic based on configuration.
3. Lock acquisition corresponding to the file type.
4. Correct writing to disk via materialized content.
5. Integration with the caching data flow (processed_content).
6. Error handling and result dictionary formation.
"""

from typing import Dict
from unittest.mock import MagicMock, mock_open, patch

import pytest

from transcriptor4ai.core.pipeline.stages.worker import process_file_task


@pytest.fixture
def mock_locks() -> Dict[str, MagicMock]:
    """
    Return a dictionary of MagicMock locks configured to support
    the context manager protocol ('with lock:').
    """
    # Create simple MagicMocks without strict specs to avoid AttributeError
    locks = {
        "module": MagicMock(),
        "test": MagicMock(),
        "resource": MagicMock(),
        "error": MagicMock(),
    }

    # Configure context manager protocol for each mock
    for lock in locks.values():
        lock.__enter__ = MagicMock(return_value=None)
        lock.__exit__ = MagicMock(return_value=None)

    return locks


@pytest.fixture
def mock_paths() -> Dict[str, str]:
    """
    Return dummy output paths for categorized transcription files.
    """
    return {
        "module": "/out/modules.txt",
        "test": "/out/tests.txt",
        "resource": "/out/resources.txt",
        "error": "/out/errors.txt",
    }


def test_worker_skips_modules_if_configured(
        mock_locks: Dict[str, MagicMock],
        mock_paths: Dict[str, str]
) -> None:
    """
    Verify that a standard code file is skipped if process_modules is False.
    """
    result = process_file_task(
        file_path="/src/main.py",
        rel_path="main.py",
        ext=".py",
        file_name="main.py",
        process_modules=False,
        process_tests=True,
        process_resources=True,
        enable_sanitizer=False,
        mask_user_paths=False,
        minify_output=False,
        locks=mock_locks,
        output_paths=mock_paths
    )

    assert result["ok"] is False
    assert result["mode"] == "skip"

    # Verify module lock was NOT used
    mock_locks["module"].__enter__.assert_not_called()


def test_worker_identifies_and_locks_tests(
        mock_locks: Dict[str, MagicMock],
        mock_paths: Dict[str, str]
) -> None:
    """
    Verify a test file is classified as 'test', uses the correct lock,
    writes to disk, and returns content for caching.
    """
    test_content = ["def test_api(): pass\n"]

    with patch("transcriptor4ai.core.pipeline.stages.worker.stream_file_content") as mock_stream, \
            patch("builtins.open", mock_open()) as mocked_file:
        mock_stream.return_value = iter(test_content)

        result = process_file_task(
            file_path="/tests/test_api.py",
            rel_path="tests/test_api.py",
            ext=".py",
            file_name="test_api.py",
            process_modules=True,
            process_tests=True,
            process_resources=True,
            enable_sanitizer=False,
            mask_user_paths=False,
            minify_output=False,
            locks=mock_locks,
            output_paths=mock_paths,
            composite_hash="hash_123"
        )

        # 1. Verify Logical Result
        assert result["ok"] is True
        assert result["mode"] == "test"
        assert result["processed_content"] == "".join(test_content)
        assert result["composite_hash"] == "hash_123"

        # 2. Verify Lock Usage
        mock_locks["test"].__enter__.assert_called_once()
        mock_locks["module"].__enter__.assert_not_called()

        # 3. Verify File System Interaction
        mocked_file.assert_called_once_with("/out/tests.txt", "a", encoding="utf-8")

        # Verify content written includes path and the materialized stream
        handle = mocked_file()
        written_calls = [call.args[0] for call in handle.write.call_args_list]
        full_output = "".join(written_calls)
        assert "tests/test_api.py" in full_output
        assert "def test_api()" in full_output


def test_worker_handles_io_error_gracefully(
        mock_locks: Dict[str, MagicMock],
        mock_paths: Dict[str, str]
) -> None:
    """
    Verify that OSError during file streaming returns failure instead of crashing.
    """
    with patch("transcriptor4ai.core.pipeline.stages.worker.stream_file_content") as mock_stream:
        # Simulate OS Permission Error
        mock_stream.side_effect = OSError("Permission denied")

        result = process_file_task(
            file_path="/src/locked.py",
            rel_path="locked.py",
            ext=".py",
            file_name="locked.py",
            process_modules=True,
            process_tests=True,
            process_resources=True,
            enable_sanitizer=False,
            mask_user_paths=False,
            minify_output=False,
            locks=mock_locks,
            output_paths=mock_paths
        )

        assert result["ok"] is False
        assert "Permission denied" in result["error"]
        assert result["mode"] == "module"


def test_worker_identifies_resources(
        mock_locks: Dict[str, MagicMock],
        mock_paths: Dict[str, str]
) -> None:
    """
    Verify that non-code resources (e.g., README.md) are correctly categorized.
    """
    with patch("transcriptor4ai.core.pipeline.stages.worker.stream_file_content") as mock_stream, \
            patch("builtins.open", mock_open()):
        mock_stream.return_value = iter(["# Project Documentation\n"])

        result = process_file_task(
            file_path="/README.md",
            rel_path="README.md",
            ext=".md",
            file_name="README.md",
            process_modules=True,
            process_tests=True,
            process_resources=True,
            enable_sanitizer=False,
            mask_user_paths=False,
            minify_output=False,
            locks=mock_locks,
            output_paths=mock_paths
        )

        assert result["ok"] is True
        assert result["mode"] == "resource"
        mock_locks["resource"].__enter__.assert_called_once()