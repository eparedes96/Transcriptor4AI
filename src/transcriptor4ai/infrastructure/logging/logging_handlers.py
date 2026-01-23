from __future__ import annotations

"""
Logging Handlers and Low-Level Utilities.

Provides specialized handler factories and internal tagging mechanisms 
to ensure that the application can distinguish its own logging 
infrastructure from external or library-injected handlers.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import Optional

# Internal attribute used to tag and identify our own handlers
_HANDLER_TAG_ATTR: str = "_transcriptor4ai_handler"


# ==============================================================================
# INTERNAL LOGGING UTILITIES
# ==============================================================================

def _tag_handler(handler: logging.Handler) -> None:
    """
    Mark a handler as an internally-managed application handler.

    Args:
        handler: The logging handler instance to tag.
    """
    try:
        setattr(handler, _HANDLER_TAG_ATTR, True)
    except Exception:
        pass


def _is_our_handler(handler: logging.Handler) -> bool:
    """
    Verify if a handler was initialized by this diagnostic module.

    Args:
        handler: The handler to inspect.

    Returns:
        bool: True if the handler carries our internal tag.
    """
    return bool(getattr(handler, _HANDLER_TAG_ATTR, False))


def _create_rotating_file_handler(
        log_file: str,
        level_int: int,
        formatter: logging.Formatter,
        max_bytes: int,
        backup_count: int,
) -> Optional[RotatingFileHandler]:
    """
    Initialize a RotatingFileHandler with robust error handling.

    Args:
        log_file: Target path for the log file.
        level_int: Numeric logging level.
        formatter: Pre-configured logging formatter.
        max_bytes: Rollover threshold in bytes.
        backup_count: Number of archived files to keep.

    Returns:
        Optional[RotatingFileHandler]: Configured handler or None if I/O fails.
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
        sys.stderr.write(f"WARNING: Diagnostic persistence failure at '{log_file}': {e}\n")
        return None


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _ensure_parent_dir(path: str) -> None:
    """
    Safely create the parent directory hierarchy for a target file.

    Args:
        path: Absolute path to the target file.
    """
    parent = os.path.dirname(os.path.abspath(path))
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)