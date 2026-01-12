from __future__ import annotations

"""
Security and Privacy Sanitizer.

Provides high-performance redaction of secrets (API Keys, IPs, Emails)
and anonymizes local system paths using stream processing.
"""

import logging
import os
import re
from pathlib import Path
from typing import Final, Iterator, Optional, Tuple

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
def _get_user_info() -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieve OS-level user info for path masking.
    Handles potential OS errors in restricted environments (CI/Docker).

    Returns:
        Tuple[Optional[str], Optional[str]]: (Username, HomeDirectory).
    """
    user_name: Optional[str] = None
    home_dir: Optional[str] = None

    try:
        user_name = os.getlogin()
    except Exception:
        try:
            user_name = os.environ.get("USER") or os.environ.get("USERNAME")
        except Exception:
            pass

    try:
        home_path = Path.home()
        home_dir = str(home_path).replace("\\", "/")
    except Exception:
        pass

    return user_name, home_dir


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def sanitize_text(text: str) -> str:
    """
    Sanitize a full string in memory.
    Useful for small snippets or configuration files.

    Args:
        text: The raw input string.

    Returns:
        str: The sanitized string with redacted secrets.
    """
    if not text:
        return ""
    return "".join(list(sanitize_text_stream(iter(text.splitlines(keepends=True)))))


def sanitize_text_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Sanitize text line-by-line using a generator.
    Redacts specific API keys, IPs, emails, and generic secret assignments.

    Args:
        lines: An iterator yielding lines of text.

    Yields:
        str: Sanitized lines.
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
    """
    Anonymize local paths in a full string.

    Args:
        text: The raw input string.

    Returns:
        str: The text with user paths replaced by <USER_HOME>.
    """
    if not text:
        return ""
    return "".join(list(mask_local_paths_stream(iter(text.splitlines(keepends=True)))))


def mask_local_paths_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Anonymize local paths line-by-line.
    Replaces the current user's home directory and username with placeholders.

    Args:
        lines: An iterator yielding lines of text.

    Yields:
        str: Masked lines.
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