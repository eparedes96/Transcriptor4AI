from __future__ import annotations

"""
Idempotent logging configuration system.

Manages console and rotating file handlers for entry points (CLI/GUI).
"""

import logging
import os
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Optional

from transcriptor4ai.paths import get_user_data_dir

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
_CONFIGURED_FLAG_ATTR = "_transcriptor4ai_configured"
_HANDLER_TAG_ATTR = "_transcriptor4ai_handler"

# =============================================================================
# Configuration Model
# =============================================================================

@dataclass(frozen=True)
class LoggingConfig:
    """
    Immutable logging configuration.

    Attributes:
        level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
        console: Enable stderr console output.
        log_file: Path to the log file (optional). Triggers RotatingFileHandler.
        max_bytes: Max size per log file before rotation.
        backup_count: Number of backup files to keep.
        console_fmt: Log format for console output.
        file_fmt: Log format for file output.
        datefmt: Date format for file logs.
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
# Internal State & Helpers
# =============================================================================

_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def _parse_level(level: str) -> int:
    if not level:
        return logging.INFO
    return _LEVEL_MAP.get(str(level).strip().upper(), logging.INFO)


def _ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)


def _tag_handler(handler: logging.Handler) -> None:
    """Mark a handler as owned by Transcriptor4AI to avoid removing external handlers."""
    try:
        setattr(handler, _HANDLER_TAG_ATTR, True)
    except Exception:
        pass


def _is_our_handler(handler: logging.Handler) -> bool:
    return bool(getattr(handler, _HANDLER_TAG_ATTR, False))


def _remove_our_handlers(root: logging.Logger) -> None:
    """Remove only the handlers created by this module."""
    for h in list(root.handlers):
        if _is_our_handler(h):
            root.removeHandler(h)
            try:
                h.close()
            except Exception:
                pass


def _add_console_handler(
    root: logging.Logger,
    level_int: int,
    formatter: logging.Formatter,
) -> None:
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level_int)
    sh.setFormatter(formatter)
    _tag_handler(sh)
    root.addHandler(sh)


def _safe_add_rotating_file_handler(
    root: logging.Logger,
    log_file: str,
    level_int: int,
    formatter: logging.Formatter,
    max_bytes: int,
    backup_count: int,
) -> None:
    """
    Attempt to add a RotatingFileHandler. Falls back to console warning on failure.
    Must never raise an exception.
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
        root.addHandler(fh)
    except Exception as e:
        # Fallback: Use console to warn about the file failure
        fallback_fmt = logging.Formatter("%(levelname)s | %(message)s")
        _add_console_handler(root, level_int, fallback_fmt)
        root.warning(
            f"Failed to initialize file logging at '{log_file}'. Error: {e}"
        )


# =============================================================================
# Public API
# =============================================================================

def get_default_gui_log_path(
    app_name: str = "Transcriptor4AI",
    file_name: str = "transcriptor4ai.log",
) -> str:
    """
    Calculate the standard OS-specific log path using paths.get_user_data_dir.

    Args:
        app_name: Kept for API compatibility (handled by paths.py).
        file_name: Name of the log file.
    """
    base_dir = get_user_data_dir()
    return os.path.join(base_dir, "logs", file_name)


def configure_logging(cfg: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """
    Configure the root logger. Idempotent unless force=True.

    This function is intended for Entrypoints (CLI/GUI) ONLY.
    """
    root = logging.getLogger()

    try:
        already = bool(getattr(root, _CONFIGURED_FLAG_ATTR, False))
        if already and not force:
            return root

        level_int = _parse_level(cfg.level)
        root.setLevel(level_int)

        # Cleanup previous Transcriptor handlers
        _remove_our_handlers(root)

        # Formatters
        console_formatter = logging.Formatter(cfg.console_fmt)
        file_formatter = logging.Formatter(cfg.file_fmt, datefmt=cfg.datefmt)

        # 1. Console Handler
        if cfg.console:
            _add_console_handler(root, level_int, console_formatter)

        # 2. File Handler
        if cfg.log_file:
            _safe_add_rotating_file_handler(
                root=root,
                log_file=cfg.log_file,
                level_int=level_int,
                formatter=file_formatter,
                max_bytes=cfg.max_bytes,
                backup_count=cfg.backup_count,
            )

        # Mark as configured
        try:
            setattr(root, _CONFIGURED_FLAG_ATTR, True)
        except Exception:
            pass

        return root

    except Exception:
        # Emergency Fallback
        try:
            fallback = logging.getLogger()
            fallback.setLevel(logging.INFO)
            _remove_our_handlers(fallback)
            _add_console_handler(
                fallback,
                logging.INFO,
                logging.Formatter("CRITICAL FALLBACK | %(levelname)s | %(message)s"),
            )
            fallback.warning("Logging configuration failed entirely. Using emergency console.")
            return fallback
        except Exception:
            return root


def get_logger(name: str) -> logging.Logger:
    """Convenience accessor for named loggers."""
    return logging.getLogger(name)