from __future__ import annotations

"""
Logging Core Orchestrator.

Maintains the idempotent lifecycle of the logging subsystem. Implements a 
non-blocking Queue architecture to ensure that I/O operations (file writing) 
do not interfere with the performance of the main execution thread or the 
responsiveness of the GUI.
"""

import atexit
import logging
import os
import queue
import sys
from logging.handlers import QueueHandler, QueueListener
from typing import List, Optional

from transcriptor4ai.infra.fs import get_user_data_dir
from transcriptor4ai.infra.logging.config import _LEVEL_MAP, LoggingConfig
from transcriptor4ai.infra.logging.handlers import (
    _create_rotating_file_handler,
    _is_our_handler,
    _tag_handler,
)

# Internal state flags for idempotency and lifecycle tracking
_CONFIGURED_FLAG_ATTR: str = "_transcriptor4ai_configured"
_QUEUE_LISTENER_ATTR: str = "_transcriptor4ai_queue_listener"


# ==============================================================================
# PUBLIC API
# ==============================================================================

def get_default_gui_log_path(
        app_name: str = "Transcriptor4AI",
        file_name: str = "transcriptor4ai.log",
) -> str:
    """
    Resolve the standard diagnostic log path within the user data directory.

    Args:
        app_name: Target application identifier.
        file_name: Target log filename.

    Returns:
        str: Absolute path to the persistent log file.
    """
    base_dir = get_user_data_dir()
    return os.path.join(base_dir, "logs", file_name)


def configure_logging(cfg: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """
    Execute idempotent configuration of the root logger using non-blocking I/O.

    Implements a QueueListener architecture to prevent main thread blocking during
    file writes. Checks internal flags to avoid redundant handler attachments
    unless explicit re-configuration is requested.

    Args:
        cfg: Structural configuration for the logging system.
        force: If True, bypass idempotency checks and re-initialize handlers.

    Returns:
        logging.Logger: The initialized root logger instance.
    """
    root = logging.getLogger()

    try:
        # 1. Idempotency Check
        already_configured = bool(getattr(root, _CONFIGURED_FLAG_ATTR, False))
        if already_configured and not force:
            return root

        level_int = _parse_level(cfg.level)
        root.setLevel(level_int)

        # Cleanup existing infrastructure to prevent handler leakage
        _remove_our_handlers(root)
        _stop_existing_listener(root)

        # 2. Handler Definition
        console_formatter = logging.Formatter(cfg.console_fmt)
        file_formatter = logging.Formatter(cfg.file_fmt, datefmt=cfg.datefmt)

        handlers_list: List[logging.Handler] = []

        if cfg.console:
            sh = logging.StreamHandler(sys.stderr)
            sh.setLevel(level_int)
            sh.setFormatter(console_formatter)
            _tag_handler(sh)
            handlers_list.append(sh)

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

        # 3. Queue-Based Orchestration (Non-blocking I/O)
        log_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)

        queue_handler = QueueHandler(log_queue)
        _tag_handler(queue_handler)

        listener = QueueListener(log_queue, *handlers_list, respect_handler_level=True)
        listener.start()

        # Attach single QueueHandler to the root to intercept all logs
        root.addHandler(queue_handler)

        # Persistence of listener state for future lifecycle management
        setattr(root, _QUEUE_LISTENER_ATTR, listener)
        setattr(root, _CONFIGURED_FLAG_ATTR, True)

        # Register cleanup to ensure logs are flushed on shutdown
        atexit.register(_safe_stop_listener, listener)

        return root

    # Fallback to emergency console logging if the infrastructure fails
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

            fallback.warning("Diagnostic infrastructure failed. Switched to emergency console.")
            return fallback
        except Exception:
            return root


def get_logger(name: str) -> logging.Logger:
    """
    Acquire a named logger instance compliant with the global configuration.

    Args:
        name: Hierarchical name for the logger (usually __name__).

    Returns:
        logging.Logger: The requested logger instance.
    """
    return logging.getLogger(name)


def get_recent_logs(n_lines: int = 100) -> str:
    """
    Extract the terminal tail of the persistent log file for diagnostics.

    Used by feedback and crash reporting modules to attach execution context.

    Args:
        n_lines: Maximum number of lines to retrieve from the file end.

    Returns:
        str: Consolidated log tail content.
    """
    log_path = get_default_gui_log_path()
    if not os.path.exists(log_path):
        return "Log file not found."

    # Use errors='replace' to avoid crashes on partially corrupted log files
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
            return "".join(lines[-n_lines:])
    except Exception as e:
        return f"Error retrieving logs: {e}"


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _parse_level(level: str) -> int:
    """Convert a string-based logging level to its numeric constant."""
    if not level:
        return logging.INFO
    return _LEVEL_MAP.get(str(level).strip().upper(), logging.INFO)


def _remove_our_handlers(root: logging.Logger) -> None:
    """Identify and detach all internally-managed handlers from the root."""
    for h in list(root.handlers):
        if _is_our_handler(h):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass


def _stop_existing_listener(root: logging.Logger) -> None:
    """Terminate and release the existing QueueListener to reset state."""
    listener = getattr(root, _QUEUE_LISTENER_ATTR, None)
    if listener:
        _safe_stop_listener(listener)
        setattr(root, _QUEUE_LISTENER_ATTR, None)


def _safe_stop_listener(listener: Optional[QueueListener]) -> None:
    """
    Safely stop a QueueListener preventing crashes on double-stop calls.

    Handles cases where the internal thread has already been joined or
    set to None, preventing AttributeError in atexit or test resets.
    """
    if not listener:
        return

    try:
        if hasattr(listener, "_thread") and listener._thread is not None:
            listener.stop()
    except Exception:
        pass