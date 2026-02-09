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

from transcriptor4ai.infrastructure.logging.logging_config import _LEVEL_MAP, LoggingConfig
from transcriptor4ai.infrastructure.logging.logging_handlers import (
    _create_rotating_file_handler,
    _is_our_handler,
    _tag_handler,
)
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

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

    Uses the FileSystemAdapter to ensure cross-platform compatibility.

    Args:
        app_name: Target application identifier.
        file_name: Target log filename.

    Returns:
        str: Absolute path to the persistent log file.
    """
    fs = FileSystemAdapter()
    base_dir = fs.get_user_data_dir()
    return os.path.join(base_dir, "logs", file_name)


def configure_logging(cfg: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """
    Execute idempotent configuration of the root logger using non-blocking I/O.

    Implements a QueueListener architecture to prevent main thread blocking during
    file writes. Checks internal flags and handler presence to avoid redundant
    attachments unless explicit re-configuration is requested.

    Args:
        cfg: Structural configuration for the logging system.
        force: If True, bypass idempotency checks and re-initialize handlers.

    Returns:
        logging.Logger: The initialized root logger instance.
    """
    root = logging.getLogger()

    try:
        # 1. VALIDATION: Strict Idempotency Check
        already_configured = bool(getattr(root, _CONFIGURED_FLAG_ATTR, False))

        # Check if our QueueHandler is actually present to handle test environment resets
        has_handler = any(isinstance(h, QueueHandler) and _is_our_handler(h) for h in root.handlers)

        if already_configured and has_handler and not force:
            return root

        # 2. PREPARATION: Resolve levels and formatters
        level_int = _parse_level(cfg.level)
        console_formatter = logging.Formatter(cfg.console_fmt)
        file_formatter = logging.Formatter(cfg.file_fmt, datefmt=cfg.datefmt)

        handlers_list: List[logging.Handler] = []

        # Setup Physical Handlers (Those behind the Queue)
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

        # 3. RECONFIGURATION: Teardown old infrastructure
        _stop_existing_listener(root)
        _remove_our_handlers(root)

        # 4. ORCHESTRATION: Start Non-blocking Async Logging
        log_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)

        # Create the listener that processes the queue in a background thread
        listener = QueueListener(log_queue, *handlers_list, respect_handler_level=True)
        listener.start()

        # The QueueHandler is the only one attached to root. It's our "Proxy".
        proxy_handler = QueueHandler(log_queue)
        _tag_handler(proxy_handler)
        root.addHandler(proxy_handler)
        root.setLevel(level_int)

        # Persistence of state
        setattr(root, _QUEUE_LISTENER_ATTR, listener)
        setattr(root, _CONFIGURED_FLAG_ATTR, True)

        # Ensure shutdown cleanup
        atexit.register(_safe_stop_listener, listener)

        return root

    except Exception as e:
        # Fallback to direct emergency console logging
        sys.stderr.write(f"CRITICAL: Logging system initialization failed: {e}\n")
        try:
            fallback = logging.getLogger()
            fallback.setLevel(logging.INFO)
            _remove_our_handlers(fallback)

            sh = logging.StreamHandler(sys.stderr)
            sh.setFormatter(logging.Formatter("FALLBACK | %(levelname)s | %(message)s"))
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
        # Check if the internal thread is alive before attempting to stop
        if hasattr(listener, "_thread") and listener._thread is not None:
            listener.stop()
    except Exception:
        pass