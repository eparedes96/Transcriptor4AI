from __future__ import annotations

"""
Integration tests for Logging Infrastructure.

Verifies the asynchronous QueueListener architecture, idempotency
of configuration, and log file rotation logic.
"""

import logging
import os
import time
from pathlib import Path
from logging.handlers import QueueListener

import pytest

from transcriptor4ai.infra.logging import (
    configure_logging,
    LoggingConfig,
    _HANDLER_TAG_ATTR,
    _QUEUE_LISTENER_ATTR
)


@pytest.fixture(autouse=True)
def reset_logging() -> None:
    """Clean up root logger handlers before and after each test."""
    root = logging.getLogger()

    listener = getattr(root, _QUEUE_LISTENER_ATTR, None)
    if listener and isinstance(listener, QueueListener):
        listener.stop()
        setattr(root, _QUEUE_LISTENER_ATTR, None)

    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()

    if hasattr(root, "_transcriptor4ai_configured"):
        delattr(root, "_transcriptor4ai_configured")


def test_logging_idempotency() -> None:
    """TC-01: Verify that multiple config calls do not duplicate handlers."""
    cfg = LoggingConfig(level="INFO", console=True)

    # First call
    configure_logging(cfg)
    root = logging.getLogger()
    initial_handler_count = len(root.handlers)

    # Second call
    configure_logging(cfg)
    assert len(root.handlers) == initial_handler_count, "Handlers were duplicated."


def test_log_rotation(tmp_path: Path) -> None:
    """TC-02: Verify file rotation when size limit is exceeded."""
    log_file = tmp_path / "test_rotate.log"
    # Set very small max_bytes for testing rotation
    cfg = LoggingConfig(
        level="DEBUG",
        log_file=str(log_file),
        max_bytes=100,  # 100 bytes
        backup_count=1
    )

    configure_logging(cfg)
    logger = logging.getLogger("test_rotate")

    # Write enough data to trigger rotation
    for i in range(10):
        logger.debug("This is a long log message to trigger rotation." * 5)

    # Give time for the QueueListener to process
    time.sleep(0.5)

    # Check if rotation happened (should see .log and .log.1)
    backup_file = tmp_path / "test_rotate.log.1"
    assert log_file.exists()
    assert backup_file.exists(), "Rotation backup file was not created."


def test_queue_listener_architecture() -> None:
    """TC-03: Verify that the root logger uses a QueueHandler-based architecture."""
    cfg = LoggingConfig(level="INFO", console=True)
    configure_logging(cfg)

    root = logging.getLogger()
    queue_handlers = [h for h in root.handlers if getattr(h, _HANDLER_TAG_ATTR, False)]

    assert len(queue_handlers) > 0
    assert hasattr(root, _QUEUE_LISTENER_ATTR)
    assert getattr(root, _QUEUE_LISTENER_ATTR) is not None