from __future__ import annotations

"""
Security and Privacy Sanitizer for Transcriptor4AI.

Provides high-performance redaction of secrets (API Keys, IPs, Emails)
and anonymizes local system paths to protect developer identity in
generated contexts.
"""

import logging
import os
import re
from pathlib import Path
from typing import Final

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Redaction Constants (Regex Patterns)
# -----------------------------------------------------------------------------
# Generic pattern for assignments like: API_KEY = "..." or "token": "..."
_GENERIC_SECRET_PATTERN: Final[str] = (
    r"(?i)(?:key|password|secret|token|auth|api|pwd)[-_]?(?:key|password|secret|token|auth|api|pwd)?\s*"
    r"[:=]\s*[\"']([^\"']{8,})[\"']"
)

# Provider Specific Patterns - V1.4.1: Support hyphens in OpenAI-like keys
_OPENAI_KEY_PATTERN: Final[str] = r"sk-[a-zA-Z0-9-]{32,}"
_AWS_KEY_PATTERN: Final[str] = r"AKIA[0-9A-Z]{16}"

# Network Patterns
_IP_PATTERN: Final[str] = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
_EMAIL_PATTERN: Final[str] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

# Pre-compiled patterns for efficiency
_COMPILED_SECRETS: Final[list[re.Pattern]] = [
    re.compile(_OPENAI_KEY_PATTERN),
    re.compile(_AWS_KEY_PATTERN),
    re.compile(_IP_PATTERN),
    re.compile(_EMAIL_PATTERN),
]

_COMPILED_ASSIGNMENTS: Final[re.Pattern] = re.compile(_GENERIC_SECRET_PATTERN)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def sanitize_text(text: str) -> str:
    """
    Redact secrets and sensitive network identifiers from the given text.

    Args:
        text: The raw source code or log content.

    Returns:
        Sanitized string with placeholders like [[REDACTED_SECRET]].
    """
    if not text:
        return ""

    # 1. Handle explicit provider keys and network info
    for pattern in _COMPILED_SECRETS:
        text = pattern.sub("[[REDACTED_SENSITIVE]]", text)

    # 2. Handle generic assignments (Key = "value")
    text = _COMPILED_ASSIGNMENTS.sub(
        lambda m: m.group(0).replace(m.group(1), "[[REDACTED_SECRET]]"),
        text
    )

    return text


def mask_local_paths(text: str) -> str:
    """
    Identify and replace local system user paths with a generic placeholder.

    Example: 'C:/Users/JohnDoe/Project' -> '<USER_HOME>/Project'
    """
    if not text:
        return ""

    try:
        user_name = os.getlogin()
        home_dir = str(Path.home()).replace("\\", "/")
    except Exception as e:
        logger.debug(f"Could not determine local user for path masking: {e}")
        return text

    # Mask full home directory path
    if home_dir:
        escaped_home = re.escape(home_dir).replace("\\/", "[\\\\/]")
        text = re.sub(escaped_home, "<USER_HOME>", text, flags=re.IGNORECASE)

    # Mask standalone username occurrences if they look like part of a path
    user_pattern = re.compile(rf"([\\/]){re.escape(user_name)}([\\/])")
    text = user_pattern.sub(r"\1<USER>\2", text)

    return text