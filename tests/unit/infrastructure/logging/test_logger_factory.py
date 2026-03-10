import logging
import queue
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path

import pytest

from transcriptor4ai.infrastructure.logging.logger_factory import (
    configure_logging,
    get_logger,
    get_recent_logs,
    get_default_gui_log_path,
    _CONFIGURED_FLAG_ATTR,
    _QUEUE_LISTENER_ATTR
)
from transcriptor4ai.infrastructure.logging.logging_config import LoggingConfig


# ==============================================================================
# TEST GROUP: LOGGING FACTORY CORE
# ==============================================================================

@pytest.fixture(autouse=True)
def cleanup_logging():
    """
    Ensures the root logger is reset before and after each test to prevent
    side effects between test cases.
    """
    root = logging.getLogger()

    # Remove existing listener if any
    listener = getattr(root, _QUEUE_LISTENER_ATTR, None)
    if listener:
        try:
            listener.stop()
        except Exception:
            pass

    # Reset internal flags and handlers
    setattr(root, _CONFIGURED_FLAG_ATTR, False)
    setattr(root, _QUEUE_LISTENER_ATTR, None)

    for h in list(root.handlers):
        root.removeHandler(h)
        h.close()

    yield


@pytest.fixture
def base_config(tmp_path):
    """Provides a valid logging configuration using a temporary directory."""
    log_file = tmp_path / "app.log"
    return LoggingConfig(
        level="DEBUG",
        console=True,
        log_file=str(log_file)
    )


def test_configure_logging_should_initialize_non_blocking_architecture(mocker, base_config):
    """
    Verifies that the factory sets up a QueueHandler and starts a QueueListener.
    """
    # 1. ARRANGE
    root = logging.getLogger()
    mock_listener = mocker.patch("transcriptor4ai.infrastructure.logging.logger_factory.QueueListener", autospec=True)

    # 2. ACT
    logger = configure_logging(base_config)

    # 3. ASSERT
    assert logger.level == logging.DEBUG
    # Check if QueueHandler was attached to root
    assert any(isinstance(h, QueueHandler) for h in root.handlers)
    # Check if Listener was started
    mock_listener.return_value.start.assert_called_once()
    assert getattr(root, _CONFIGURED_FLAG_ATTR) is True


def test_configure_logging_idempotency_should_prevent_duplicate_handlers(mocker, base_config):
    """
    Ensures that multiple calls to configure_logging do not stack redundant handlers.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.infrastructure.logging.logger_factory.QueueListener")

    # 2. ACT
    configure_logging(base_config)
    initial_handler_count = len(logging.getLogger().handlers)

    # Call again without force
    configure_logging(base_config)

    # 3. ASSERT
    assert len(logging.getLogger().handlers) == initial_handler_count
    assert initial_handler_count > 0


def test_configure_logging_with_force_should_reinitialize_system(mocker, base_config):
    """
    Verifies that the 'force' flag bypasses idempotency and recreates the listener.
    """
    # 1. ARRANGE
    mock_listener = mocker.patch("transcriptor4ai.infrastructure.logging.logger_factory.QueueListener")

    # 2. ACT
    configure_logging(base_config)
    configure_logging(base_config, force=True)

    # 3. ASSERT
    # Should be called once for first config, once to stop old one (mock logic),
    # and again for second config
    assert mock_listener.return_value.start.call_count == 2


def test_configure_logging_fallback_on_critical_failure(mocker, base_config):
    """
    Sad Path: If directory creation or listener startup fails, should
    fall back to emergency StreamHandler.
    """
    # 1. ARRANGE
    # Simulate a critical failure during handler creation
    mocker.patch(
        "transcriptor4ai.infrastructure.logging.logger_factory._create_rotating_file_handler",
        side_effect=RuntimeError("Disk is on fire")
    )
    mock_stderr = mocker.patch("sys.stderr.write")

    # 2. ACT
    logger = configure_logging(base_config, force=True)

    # 3. ASSERT
    assert logger is not None
    # Verify fallback: Root should have at least one handler (the emergency one)
    assert len(logger.handlers) >= 1
    mock_stderr.assert_called()


def test_get_logger_returns_consistent_named_instance():
    """Verifies that get_logger is a reliable proxy for logging.getLogger."""
    # 1. ACT
    log_a = get_logger("transcriptor.test")
    log_b = get_logger("transcriptor.test")

    # 2. ASSERT
    assert log_a.name == "transcriptor.test"
    assert log_a is log_b


def test_get_recent_logs_should_return_tail_of_file(tmp_path):
    """Verifies that we can retrieve the last N lines from the physical log file."""
    # 1. ARRANGE
    log_file = tmp_path / "test_tail.log"
    content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
    log_file.write_text(content, encoding="utf-8")

    mocker_path = "transcriptor4ai.infrastructure.logging.logger_factory.get_default_gui_log_path"
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr(mocker_path, lambda: str(log_file))

        # 2. ACT
        tail = get_recent_logs(n_lines=2)

        # 3. ASSERT
        assert "Line 4" in tail
        assert "Line 5" in tail
        assert "Line 1" not in tail


def test_get_recent_logs_handles_missing_file(mocker):
    """Sad Path: Should return a descriptive message if log file is absent."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=False)

    # 2. ACT
    result = get_recent_logs()

    # 3. ASSERT
    assert "Log file not found" in result


def test_get_default_gui_log_path_resolution(mocker):
    """Ensures the path resolution logic uses the FileSystem adapter correctly."""
    # 1. ARRANGE
    mock_fs = mocker.patch("transcriptor4ai.infrastructure.logging.logger_factory.FileSystemAdapter")
    mock_fs.return_value.get_user_data_dir.return_value = "/mock/data"

    # 2. ACT
    path = get_default_gui_log_path()

    # 3. ASSERT
    assert "/mock/data" in path
    assert "transcriptor4ai.log" in path