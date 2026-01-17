from __future__ import annotations

"""
Security and Privacy Sanitization Service.

Implements high-performance redaction of sensitive information including 
API Keys, IP addresses, and emails using optimized regex patterns. 
Additionally, provides anonymization for local system paths to protect 
user identity when sharing codebase contexts with AI providers.
"""

import logging
import os
import re
import functools
from pathlib import Path
from typing import Final, Iterator, Optional, Tuple

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# SECURITY PATTERNS
# -----------------------------------------------------------------------------

_GENERIC_SECRET_PATTERN: Final[str] = (
    r"(?i)(?:key|password|secret|token|auth|api|pwd)[-_]?(?:key|password|secret|token|auth|api|pwd)?\s*"
    r"[:=]\s*['\"]([^'\"]{8,})['\"]"
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
# ENVIRONMENT INSPECTION
# -----------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def _get_user_info() -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieve OS-level user metadata with memoization.

    Detects the current username and home directory path to build
    anonymization rules. Cached to prevent expensive OS calls during
    high-volume stream processing.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing (Username, HomeDirectory).
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
# REDACTION API
# -----------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """
    Redact secrets and PII from a full string in-memory.

    Args:
        text: Raw input string.

    Returns:
        str: Sanitized string with redacted sensitive data.
    """
    if not text:
        return ""
    return "".join(list(sanitize_text_stream(iter(text.splitlines(keepends=True)))))


def sanitize_text_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Process a text stream to redact sensitive patterns on-the-fly.

    Target patterns include cloud provider keys, network addresses,
    and generic variable assignments that resemble credentials.

    Args:
        lines: Iterator yielding lines of text.

    Yields:
        str: Sanitized text lines.
    """
    for line in lines:
        if not line.strip():
            yield line
            continue

        processed = line

        # Redact hardcoded specific signatures
        for pattern in _COMPILED_SECRETS:
            processed = pattern.sub("[[REDACTED_SENSITIVE]]", processed)

        # Redact credential assignments using group replacement
        processed = _COMPILED_ASSIGNMENTS.sub(
            lambda m: m.group(0).replace(m.group(1), "[[REDACTED_SECRET]]"),
            processed
        )
        yield processed

# -----------------------------------------------------------------------------
# PATH ANONYMIZATION API
# -----------------------------------------------------------------------------

def mask_local_paths(text: str) -> str:
    """
    Replace local filesystem paths with anonymous placeholders in a full string.

    Args:
        text: Raw input string.

    Returns:
        str: Anonymized text.
    """
    if not text:
        return ""
    return "".join(list(mask_local_paths_stream(iter(text.splitlines(keepends=True)))))


def mask_local_paths_stream(lines: Iterator[str]) -> Iterator[str]:
    """
    Process a text stream to mask local environment identifiers.

    Identifies the user's home directory and standalone username
    occurrences, replacing them with generic placeholders to prevent
    local environment leakage.

    Args:
        lines: Iterator yielding lines of text.

    Yields:
        str: Masked text lines.
    """
    user_name, home_dir = _get_user_info()

    # Pre-compile dynamic patterns once for the stream duration
    patterns = []
    if home_dir:
        patterns.append((re.compile(re.escape(home_dir), re.IGNORECASE), "<USER_HOME>"))
    if user_name:
        patterns.append((re.compile(rf"([\\/]){re.escape(user_name)}([\\/])"), r"\1<USER>\2"))

    # Normalize separators before replacement
    for line in lines:
        processed = line.replace("\\", "/")

        for pattern, replacement in patterns:
            processed = pattern.sub(replacement, processed)

        yield processed