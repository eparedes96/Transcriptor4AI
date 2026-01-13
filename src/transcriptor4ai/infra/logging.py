from __future__ import annotations

"""
Logging Infrastructure.

Implements an idempotent, fail-safe logging configuration system.
It supports:
- Console output (stderr) for CLI feedback.
- Rotating file logging for persistent diagnostics.
- Thread-safe handler management to avoid duplication.
"""

import atexit
import logging
import os
import sys
import queue
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler, QueueHandler, QueueListener
from typing import Optional, Dict

from transcriptor4ai.infra.fs import get_user_data_dir

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_CONFIGURED_FLAG_ATTR: str = "_transcriptor4ai_configured"
_HANDLER_TAG_ATTR: str = "_transcriptor4ai_handler"
_QUEUE_LISTENER_ATTR: str = "_transcriptor4ai_queue_listener"

_LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


# =============================================================================
# Configuration Model
# =============================================================================

@dataclass(frozen=True)
class LoggingConfig:
    """
    Immutable logging configuration parameters.

    Attributes:
        level: Logging level string ("DEBUG", "INFO", etc.).
        console: Whether to enable console (stderr) logging.
        log_file: Optional path to a log file. Enables rotation if set.
        max_bytes: Max size in bytes before log rotation (default 2MB).
        backup_count: Number of backup log files to keep.
        console_fmt: Format string for console output.
        file_fmt: Format string for file output.
        datefmt: Date format string.
    """
    level: str = "INFO"
    console: bool = True
    log_file: Optional[str] = None

    max_bytes: int = 2 * 1024 * 1024  # 2 MB
    backup_count: int = 3

    console_fmt: str = "%(levelname)s | %(message)s"
    file_fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"


# =============================================================================
# Public API
# =============================================================================

def get_default_gui_log_path(
        app_name: str = "Transcriptor4AI",
        file_name: str = "transcriptor4ai.log",
) -> str:
    """
    Calculate the standard OS-specific log path using the user data directory.

    Args:
        app_name: Name of the application (used for folder structure).
        file_name: Name of the log file itself.

    Returns:
        str: Absolute path to the log file.
    """
    base_dir = get_user_data_dir()
    return os.path.join(base_dir, "logs", file_name)


def configure_logging(cfg: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """
    Configure the root logger with the provided settings using QueueHandler.

    This function is idempotent: it checks if logging has already been configured
    by this module to prevent duplicate handlers, unless `force=True`.

    This uses a non-blocking QueueHandler to decouple logging I/O
    from the main application thread (crucial for GUI responsiveness).

    Args:
        cfg: Configuration object.
        force: If True, re-configure even if already setup.

    Returns:
        logging.Logger: The configured root logger instance.
    """
    root = logging.getLogger()

    try:
        already_configured = bool(getattr(root, _CONFIGURED_FLAG_ATTR, False))
        if already_configured and not force:
            return root

        level_int = _parse_level(cfg.level)
        root.setLevel(level_int)

        # Cleanup previous handlers and listeners
        _remove_our_handlers(root)
        _stop_existing_listener(root)

        # Formatters
        console_formatter = logging.Formatter(cfg.console_fmt)
        file_formatter = logging.Formatter(cfg.file_fmt, datefmt=cfg.datefmt)

        handlers_list = []

        # 1. Console Handler (Direct stderr)
        if cfg.console:
            sh = logging.StreamHandler(sys.stderr)
            sh.setLevel(level_int)
            sh.setFormatter(console_formatter)
            _tag_handler(sh)
            handlers_list.append(sh)

        # 2. File Handler (Rotating)
        if cfg.log_file:
            fh = _create_rotating_file_handler(
                cfg.log_file,
                level_int,
                file_formatter,
                cfg.max_bytes,
                cfg.backup_count
            )
            if fh:
                handlers_list.append(fh)

        if not handlers_list:
            return root

        # 3. Thread-Safety: Setup QueueListener
        log_queue = queue.Queue(-1)  # Unlimited size
        queue_handler = QueueHandler(log_queue)
        _tag_handler(queue_handler)

        listener = QueueListener(log_queue, *handlers_list, respect_handler_level=True)
        listener.start()

        # Attach QueueHandler to root
        root.addHandler(queue_handler)

        # Store reference to listener to stop it later
        setattr(root, _QUEUE_LISTENER_ATTR, listener)
        setattr(root, _CONFIGURED_FLAG_ATTR, True)

        # Ensure listener stops at exit
        atexit.register(listener.stop)

        return root

    except Exception:
        try:
            fallback = logging.getLogger()
            fallback.setLevel(logging.INFO)
            _remove_our_handlers(fallback)
            _stop_existing_listener(fallback)

            sh = logging.StreamHandler(sys.stderr)
            sh.setFormatter(logging.Formatter("CRITICAL FALLBACK | %(levelname)s | %(message)s"))
            _tag_handler(sh)
            fallback.addHandler(sh)

            fallback.warning("Logging configuration failed entirely. Using emergency console.")
            return fallback
        except Exception:
            return root


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.

    Args:
        name: The name of the logger (typically __name__).

    Returns:
        logging.Logger: The logger instance.
    """
    return logging.getLogger(name)


def get_recent_logs(n_lines: int = 100) -> str:
    """
    Retrieve the tail of the active application log file.
    Used for creating crash reports and feedback attachments.

    Args:
        n_lines: Number of lines to retrieve from the end.

    Returns:
        str: The last N lines of the log as a single string.
    """
    log_path = get_default_gui_log_path()
    if not os.path.exists(log_path):
        return "Log file not found."

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-n_lines:])
    except Exception as e:
        return f"Error retrieving logs: {e}"


# =============================================================================
# Private Helpers
# =============================================================================

def _parse_level(level: str) -> int:
    """Convert a string level name to its logging integer constant."""
    if not level:
        return logging.INFO
    return _LEVEL_MAP.get(str(level).strip().upper(), logging.INFO)


def _ensure_parent_dir(path: str) -> None:
    """Recursively create the directory structure for a file path."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _tag_handler(handler: logging.Handler) -> None:
    """Tag a handler instance as 'owned' by Transcriptor4AI."""
    try:
        setattr(handler, _HANDLER_TAG_ATTR, True)
    except Exception:
        pass


def _is_our_handler(handler: logging.Handler) -> bool:
    """Check if a handler instance was created by this module."""
    return bool(getattr(handler, _HANDLER_TAG_ATTR, False))


def _remove_our_handlers(root: logging.Logger) -> None:
    """Remove only the handlers tagged as ours from the logger."""
    for h in list(root.handlers):
        if _is_our_handler(h):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass


def _stop_existing_listener(root: logging.Logger) -> None:
    """Stop and cleanup any existing QueueListener attached to root."""
    listener = getattr(root, _QUEUE_LISTENER_ATTR, None)
    if listener and isinstance(listener, QueueListener):
        listener.stop()
        setattr(root, _QUEUE_LISTENER_ATTR, None)


def _create_rotating_file_handler(
        log_file: str,
        level_int: int,
        formatter: logging.Formatter,
        max_bytes: int,
        backup_count: int,
) -> Optional[RotatingFileHandler]:
    """
    Attempt to create a RotatingFileHandler safely.
    Returns None if file access fails.
    """
    try:
        _ensure_parent_dir(log_file)
        fh = RotatingFileHandler(
            log_file,
            maxBytes=int(max_bytes),
            backupCount=int(backup_count),
            encoding="utf-8",
        )
        fh.setLevel(level_int)
        fh.setFormatter(formatter)
        _tag_handler(fh)
        return fh
    except Exception as e:
        sys.stderr.write(f"WARNING: Failed to initialize file logging at '{log_file}': {e}\n")
        return None