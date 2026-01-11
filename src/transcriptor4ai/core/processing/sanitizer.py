from __future__ import annotations

"""
Security and Privacy Sanitizer for Transcriptor4AI.

Provides high-performance redaction of secrets (API Keys, IPs, Emails) and anonymizes local system paths.
Supports streaming/iterator-based processing for massive file support.
"""

import logging
import os
import re
from pathlib import Path
from typing import Final, Iterator, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Redaction Constants (Regex Patterns)
# -----------------------------------------------------------------------------
_GENERIC_SECRET_PATTERN: Final[str] = (
    r"(?i)(?:key|password|secret|token|auth|api|pwd)[-_]?(?:key|password|secret|token|auth|api|pwd)?\s*"
    r"[:=]\s*[\"']([^\"']{8,})[\"']"
)

_OPENAI_KEY_PATTERN: Final[str] = r"sk-[a-zA-Z0-9-]{32,}"
_AWS_KEY_PATTERN: Final[str] = r"AKIA[0-9A-Z]{16}"

_IP_PATTERN: Final[str] = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
_EMAIL_PATTERN: Final[str] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

_COMPILED_SECRETS: Final[list[re.Pattern]] = [
    re.compile(_OPENAI_KEY_PATTERN),
    re.compile(_AWS_KEY_PATTERN),
    re.compile(_IP_PATTERN),
    re.compile(_EMAIL_PATTERN),
]

_COMPILED_ASSIGNMENTS: Final[re.Pattern] = re.compile(_GENERIC_SECRET_PATTERN)


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------

def _get_user_info() -> tuple[Optional[str], Optional[str]]:
    """Retrieve OS-level user info for path masking."""
    try:
        user_name = os.getlogin()
        home_dir = str(Path.home()).replace("\\", "/")
        return user_name, home_dir
    except Exception as e:
        logger.debug(f"Could not determine local user for path masking: {e}")
        return None, None


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """
    Standard string-based sanitization.
    Maintained for backward compatibility and small file processing.
    """
    if not text:
        return ""

    return "".join(list(sanitize_text_stream(text.splitlines(keepends=True))))


def sanitize_text_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Stream-based sanitization. Redacts secrets line by line.

    Args:
        lines: An iterator of raw text lines.

    Yields:
        Sanitized lines with placeholders.
    """
    for line in lines:
        if not line.strip():
            yield line
            continue

        processed = line
        # 1. Redact specific provider keys and network info
        for pattern in _COMPILED_SECRETS:
            processed = pattern.sub("[[REDACTED_SENSITIVE]]", processed)

        # 2. Redact generic assignments
        processed = _COMPILED_ASSIGNMENTS.sub(
            lambda m: m.group(0).replace(m.group(1), "[[REDACTED_SECRET]]"),
            processed
        )
        yield processed


def mask_local_paths(text: str) -> str:
    """Standard string-based path masking."""
    if not text:
        return ""
    return "".join(list(mask_local_paths_stream(text.splitlines(keepends=True))))


def mask_local_paths_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Stream-based path masking. Replaces local paths with <USER_HOME>.

    Args:
        lines: An iterator of raw text lines.

    Yields:
        Masked lines.
    """
    user_name, home_dir = _get_user_info()

    # Pre-compile patterns if info is available to optimize the stream
    home_pattern = None
    user_pattern = None
    if home_dir:
        home_pattern = re.compile(re.escape(home_dir), re.IGNORECASE)
    if user_name:
        user_pattern = re.compile(rf"([\\/]){re.escape(user_name)}([\\/])")

    for line in lines:
        processed = line.replace("\\", "/")

        if home_pattern:
            processed = home_pattern.sub("<USER_HOME>", processed)

        if user_pattern:
            processed = user_pattern.sub(r"\1<USER>\2", processed)

        yield processed