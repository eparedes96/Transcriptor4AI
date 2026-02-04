from __future__ import annotations

import logging
import os
import time
import queue
from pathlib import Path

import pytest

from transcriptor4ai.infrastructure.logging.logger_factory import configure_logging, _stop_existing_listener
from transcriptor4ai.infrastructure.logging.logging_config import LoggingConfig


# ==============================================================================
# TEST GROUP: LOGGING INFRASTRUCTURE INTEGRATION
# ==============================================================================

@pytest.fixture(autouse=True)
def cleanup_logging():
    """Ensures a clean logging state before and after each test."""
    yield
    root = logging.getLogger()
    _stop_existing_listener(root)
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()


@pytest.mark.integration
def test_logging_should_rotate_when_size_limit_is_exceeded(tmp_path: Path):
    """
    Verifies that the RotatingFileHandler correctly splits logs into backup files
    once the byte limit is reached.
    """
    # 1. ARRANGE: Set a very small max_bytes to trigger rotation quickly
    log_file = tmp_path / "test_rotation.log"
    config = LoggingConfig(
        level="INFO",
        console=False,
        log_file=str(log_file),
        max_bytes=100,  # Tiny limit for testing
        backup_count=2
    )

    # 2. ACT: Initialize and write enough data to exceed 100 bytes multiple times
    configure_logging(config, force=True)
    logger = logging.getLogger("test_rotation_logger")

    # We write multiple times to ensure rotation happens
    for i in range(10):
        logger.info(f"Log message number {i} - padding to exceed bytes")
        # Small sleep to allow the QueueListener to process the message
        time.sleep(0.05)

    # 3. ASSERT: Verify the existence of rotated files
    # The main file plus up to 2 backups
    assert log_file.exists()
    assert (tmp_path / "test_rotation.log.1").exists()

    # Check that it doesn't exceed the backup count
    # (files should be: log, log.1, log.2. log.3 should NOT exist)
    assert not (tmp_path / "test_rotation.log.3").exists()


@pytest.mark.integration
def test_logging_should_fail_gracefully_when_directory_is_readonly(mocker, tmp_path: Path):
    """
    Ensures the application doesn't crash if it cannot write to the log directory.
    The factory should handle the OSError and return a fallback logger.
    """
    # 1. ARRANGE: Mock os.makedirs to simulate a permission error
    log_file = tmp_path / "readonly_dir" / "app.log"
    mocker.patch("os.makedirs", side_effect=OSError("Permission denied"))

    config = LoggingConfig(
        level="INFO",
        log_file=str(log_file)
    )

    # 2. ACT: Attempt to configure logging
    # We also monitor stderr since the code writes a warning there
    mock_stderr = mocker.patch("sys.stderr.write")
    logger = configure_logging(config, force=True)

    # 3. ASSERT: Execution continues and fallback to console/no-op happens
    assert logger is not None
    assert mock_stderr.called
    # The first argument of stderr.write contains the warning message
    assert "Diagnostic persistence failure" in mock_stderr.call_args[0][0]


@pytest.mark.integration
def test_logging_queue_listener_should_handle_concurrent_calls(tmp_path: Path):
    """
    Verifies that the non-blocking architecture handles high-frequency logs
    without data loss or thread contention.
    """
    # 1. ARRANGE: Setup standard config
    log_file = tmp_path / "concurrent.log"
    config = LoggingConfig(
        level="DEBUG",
        log_file=str(log_file)
    )
    configure_logging(config, force=True)
    logger = logging.getLogger("concurrent_test")

    # 2. ACT: Rapid fire logs
    message_count = 50
    for i in range(message_count):
        logger.debug(f"Message_{i}")

    # Wait for QueueListener to finish flushing
    time.sleep(0.5)

    # 3. ASSERT: All messages should be present in the file
    content = log_file.read_text(encoding="utf-8")
    for i in range(message_count):
        assert f"Message_{i}" in content


@pytest.mark.integration
def test_logging_should_prevent_duplicate_handlers_on_reconfiguration(tmp_path: Path):
    """
    Ensures that calling configure_logging multiple times does not
    attach redundant handlers (Idempotency).
    """
    # 1. ARRANGE: Initial setup
    log_file = tmp_path / "idempotent.log"
    config = LoggingConfig(log_file=str(log_file))

    # 2. ACT: Configure twice
    configure_logging(config, force=False)
    configure_logging(config, force=False)

    root = logging.getLogger()
    # In our architecture, we use a QueueHandler attached to root
    # which points to a Listener managing the real handlers.
    queue_handlers = [h for h in root.handlers if isinstance(h, logging.handlers.QueueHandler)]

    # 3. ASSERT: Only one QueueHandler should exist on the root logger
    assert len(queue_handlers) == 1