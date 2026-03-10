import logging
import os
from logging.handlers import RotatingFileHandler

import pytest

from transcriptor4ai.infrastructure.logging.logging_handlers import (
    _HANDLER_TAG_ATTR,
    _create_rotating_file_handler,
    _ensure_parent_dir,
    _is_our_handler,
    _tag_handler,
)


# ==============================================================================
# TEST GROUP: HANDLER IDENTIFICATION (TAGGING)
# ==============================================================================

def test_tag_handler_should_attach_internal_attribute(mocker):
    """
    Verifies that _tag_handler marks a handler with the internal application signature.
    """
    # 1. ARRANGE: Set up a generic handler mock
    mock_handler = mocker.Mock(spec=logging.Handler)

    # 2. ACT: Execute the tagging logic
    _tag_handler(mock_handler)

    # 3. ASSERT: Verify the internal attribute is present
    assert hasattr(mock_handler, _HANDLER_TAG_ATTR)
    assert getattr(mock_handler, _HANDLER_TAG_ATTR) is True


def test_is_our_handler_should_detect_internal_signature(mocker):
    """
    Ensures _is_our_handler can differentiate between app-managed and external handlers.
    """
    # 1. ARRANGE: Create one tagged handler and one clean handler
    our_handler = mocker.Mock(spec=logging.Handler)
    setattr(our_handler, _HANDLER_TAG_ATTR, True)

    ext_handler = mocker.Mock(spec=logging.Handler)

    # 2. ACT & 3. ASSERT: Verify the identification logic
    assert _is_our_handler(our_handler) is True
    assert _is_our_handler(ext_handler) is False


# ==============================================================================
# TEST GROUP: DIRECTORY MANAGEMENT
# ==============================================================================

def test_ensure_parent_dir_should_create_missing_hierarchy(mocker):
    """
    Validates that the utility identifies and creates the directory structure for a log file.
    Fixes path normalization issues across different operating systems.
    """
    # 1. ARRANGE: Prepare OS-agnostic path and mocks
    log_path = "/mock/logs/app.log"
    # Resolve absolute expected directory using the same logic as the SUT
    expected_dir = os.path.dirname(os.path.abspath(log_path))

    mock_exists = mocker.patch("os.path.exists", return_value=False)
    mock_makedirs = mocker.patch("os.makedirs")

    # 2. ACT: Trigger directory validation
    _ensure_parent_dir(log_path)

    # 3. ASSERT: Verify os calls are consistent with OS-specific path normalization
    mock_exists.assert_called_once_with(expected_dir)
    mock_makedirs.assert_called_once_with(expected_dir, exist_ok=True)


def test_ensure_parent_dir_should_ignore_existing_paths(mocker):
    """
    Ensures no unnecessary OS calls are made if the directory already exists.
    """
    # 1. ARRANGE: Mock path as already existing
    mocker.patch("os.path.exists", return_value=True)
    mock_makedirs = mocker.patch("os.makedirs")

    # 2. ACT: Try to ensure an existing path
    _ensure_parent_dir("/existing/path/log.txt")

    # 3. ASSERT: makedirs should not be called
    mock_makedirs.assert_not_called()


# ==============================================================================
# TEST GROUP: HANDLER FACTORY
# ==============================================================================

def test_create_rotating_file_handler_success(mocker):
    """
    Verifies that a RotatingFileHandler is correctly instantiated, configured, and tagged.
    """
    # 1. ARRANGE: Mock internal logic and target class
    mocker.patch("transcriptor4ai.infrastructure.logging.logging_handlers._ensure_parent_dir")
    mock_rfh_cls = mocker.patch(
        "transcriptor4ai.infrastructure.logging.logging_handlers.RotatingFileHandler",
        autospec=True
    )

    fmt = logging.Formatter("%(message)s")
    path = "/tmp/test.log"

    # 2. ACT: Instantiate the handler
    handler = _create_rotating_file_handler(
        log_file=path,
        level_int=logging.DEBUG,
        formatter=fmt,
        max_bytes=1000,
        backup_count=5
    )

    # 3. ASSERT: Check constructor, config and tagging
    assert handler is not None
    mock_rfh_cls.assert_called_once_with(
        path, maxBytes=1000, backupCount=5, encoding="utf-8"
    )
    handler.setLevel.assert_called_with(logging.DEBUG)
    handler.setFormatter.assert_called_with(fmt)
    assert _is_our_handler(handler) is True


def test_create_rotating_file_handler_handles_permission_errors_gracefully(mocker):
    """
    Sad Path: If the filesystem is read-only or access is denied,
    it should return None and log to stderr instead of crashing.
    """
    # 1. ARRANGE: Simulate Permission Error
    mocker.patch(
        "transcriptor4ai.infrastructure.logging.logging_handlers._ensure_parent_dir",
        side_effect=PermissionError("Access Denied")
    )
    mock_stderr = mocker.patch("sys.stderr.write")

    # 2. ACT: Attempt creation in protected path
    handler = _create_rotating_file_handler(
        "/root/protected.log", logging.INFO, logging.Formatter(), 0, 0
    )

    # 3. ASSERT: Verify safe failure
    assert handler is None
    mock_stderr.assert_called()
    assert "persistence failure" in mock_stderr.call_args[0][0]


@pytest.mark.parametrize("input_val, expected", [
    (1024, 1024),
    ("2048", 2048),
])
def test_create_rotating_file_handler_coerces_numeric_parameters(mocker, input_val, expected):
    """
    Ensures the factory is robust against stringified numeric inputs from config files.
    """
    # 1. ARRANGE: Mock infrastructure
    mocker.patch("transcriptor4ai.infrastructure.logging.logging_handlers._ensure_parent_dir")
    mock_rfh = mocker.patch("transcriptor4ai.infrastructure.logging.logging_handlers.RotatingFileHandler")

    # 2. ACT: Call with potentially stringified inputs
    _create_rotating_file_handler("log.txt", logging.INFO, logging.Formatter(), input_val, input_val)

    # 3. ASSERT: constructor should receive clean integers
    args, kwargs = mock_rfh.call_args
    assert kwargs["maxBytes"] == expected
    assert kwargs["backupCount"] == expected