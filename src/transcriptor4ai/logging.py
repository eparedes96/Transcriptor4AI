# src/transcriptor4ai/logging.py
from __future__ import annotations

"""
Centralized logging configuration for Transcriptor4AI.

Design goals:
- Entrypoint-owned: only CLI/GUI call configure_logging().
- Idempotent: avoid duplicated handlers across re-entrancy/tests.
- Fail-safe: logging must never break the main flow.
- GUI-friendly: default rotating log file in an OS-appropriate location.
"""

import logging
import os
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Optional


# =============================================================================
# Configuration model
# =============================================================================

@dataclass(frozen=True)
class LoggingConfig:
    """
    Stable logging configuration.

    - level: "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"
    - console: enable stderr console output
    - log_file: file path (optional). When provided, a rotating file handler is used.
    - max_bytes / backup_count: rotation parameters for file logging
    - console_fmt / file_fmt: formats for console and file
    - datefmt: timestamp format for file logs
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
# Internal state and helpers
# =============================================================================

_CONFIGURED_FLAG_ATTR = "_transcriptor4ai_configured"
_HANDLER_TAG_ATTR = "_transcriptor4ai_handler"

_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,  # tolerance
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
    try:
        setattr(handler, _HANDLER_TAG_ATTR, True)
    except Exception:
        pass


def _is_our_handler(handler: logging.Handler) -> bool:
    return bool(getattr(handler, _HANDLER_TAG_ATTR, False))


def _remove_our_handlers(root: logging.Logger) -> None:
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
    Attempt to add a rotating file handler. If it fails, fall back to stderr.

    This function must never raise.
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
    except Exception:
        fallback_fmt = logging.Formatter("%(levelname)s | %(message)s")
        _add_console_handler(root, level_int, fallback_fmt)
        root.warning(
            "Failed to initialize file logging; falling back to console. log_file=%s",
            log_file,
        )


# =============================================================================
# Public API
# =============================================================================

def get_default_gui_log_path(
    app_name: str = "Transcriptor4AI",
    file_name: str = "transcriptor4ai.log",
) -> str:
    """
    Return a default GUI log path.

    Windows: %LOCALAPPDATA%\\<app_name>\\logs\\<file_name>
    Fallback: ~/.transcriptor4ai/logs/<file_name>
    """
    try:
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                return os.path.join(base, app_name, "logs", file_name)
    except Exception:
        pass

    # Cross-platform fallback
    home = os.path.expanduser("~")
    return os.path.join(home, ".transcriptor4ai", "logs", file_name)


def build_config_from_dict(d: dict) -> LoggingConfig:
    """
    Build LoggingConfig from a dict (e.g. config.json).

    Accepted keys (tolerant):
      - logging_level / log_level
      - logging_console
      - logging_file / log_file
    """
    level = str(d.get("logging_level") or d.get("log_level") or "INFO")
    console = bool(d.get("logging_console", True))
    log_file = d.get("logging_file") or d.get("log_file") or None
    return LoggingConfig(level=level, console=console, log_file=log_file)


def configure_logging(cfg: LoggingConfig, *, force: bool = False) -> logging.Logger:
    """
    Configure the root logger in an idempotent way.

    Behavior:
    - If already configured by Transcriptor4AI and force=False: no-op.
    - Otherwise: remove only handlers previously added by Transcriptor4AI and
      (re)apply config.
    - Never raises.

    Note:
    - This is meant to be called ONLY from entrypoints (CLI/GUI).
    - Core/services should call get_logger(__name__) only.
    """
    root = logging.getLogger()

    try:
        already = bool(getattr(root, _CONFIGURED_FLAG_ATTR, False))
        if already and not force:
            return root

        level_int = _parse_level(cfg.level)
        root.setLevel(level_int)

        # Remove only our handlers to avoid breaking external logging setup.
        _remove_our_handlers(root)

        # Prepare formatters
        console_formatter = logging.Formatter(cfg.console_fmt)
        file_formatter = logging.Formatter(cfg.file_fmt, datefmt=cfg.datefmt)

        # Console
        if cfg.console:
            _add_console_handler(root, level_int, console_formatter)

        # File (rotating)
        if cfg.log_file:
            _safe_add_rotating_file_handler(
                root=root,
                log_file=cfg.log_file,
                level_int=level_int,
                formatter=file_formatter,
                max_bytes=cfg.max_bytes,
                backup_count=cfg.backup_count,
            )

        try:
            setattr(root, _CONFIGURED_FLAG_ATTR, True)
        except Exception:
            pass

        return root

    except Exception:
        try:
            fallback = logging.getLogger()
            fallback.setLevel(logging.INFO)
            _remove_our_handlers(fallback)
            _add_console_handler(
                fallback,
                logging.INFO,
                logging.Formatter("%(levelname)s | %(message)s"),
            )
            try:
                setattr(fallback, _CONFIGURED_FLAG_ATTR, True)
            except Exception:
                pass
            fallback.warning("Logging configuration failed; using emergency console logger.")
            return fallback
        except Exception:
            return root


def get_logger(name: str) -> logging.Logger:
    """
    Convenience helper to obtain a named logger.
    """
    return logging.getLogger(name)