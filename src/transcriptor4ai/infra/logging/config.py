from __future__ import annotations

"""
Logging Configuration Models.

Defines the data structures and constants required to initialize the 
logging subsystem. Includes the primary configuration dataclass and 
severity level mappings.
"""

import logging
from dataclasses import dataclass
from typing import Dict, Optional

# Mapping of string identifiers to native logging constants
_LEVEL_MAP: Dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "WARN": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


@dataclass(frozen=True)
class LoggingConfig:
    """
    Immutable specification for the logging subsystem initialization.

    Attributes:
        level: Minimum severity level to capture.
        console: Flag to enable stderr stream output.
        log_file: Optional absolute path for persistent file storage.
        max_bytes: Maximum size per log segment before rotation.
        backup_count: Number of historical log segments to preserve.
        console_fmt: Structural format for terminal output.
        file_fmt: Structural format for file entries.
        datefmt: Chronological format for timestamp generation.
    """
    level: str = "INFO"
    console: bool = True
    log_file: Optional[str] = None

    max_bytes: int = 2 * 1024 * 1024  # Default: 2MB
    backup_count: int = 3

    console_fmt: str = "%(levelname)s | %(message)s"
    file_fmt: str = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    datefmt: str = "%Y-%m-%d %H:%M:%S"