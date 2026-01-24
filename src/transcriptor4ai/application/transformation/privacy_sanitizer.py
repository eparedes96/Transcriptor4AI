from __future__ import annotations

"""
Privacy and Security Sanitization Service.

Implements high-performance redaction of sensitive information including 
API Keys, IP addresses, and emails using optimized regex patterns. 
Provides anonymization for local system paths by injecting user context.
Supports both in-memory and streaming processing modes.
"""

import logging
import re
from typing import Final, Iterator, List, Optional, Tuple

from transcriptor4ai.domain.ports.user_port import IUserContext

logger = logging.getLogger(__name__)

# ==============================================================================
# STATIC SECURITY PATTERNS
# ==============================================================================

# Generic pattern for assignments: KEY = "value" (Minimum 8 chars for the secret)
_GENERIC_SECRET_PATTERN: Final[str] = (
    r"(?i)(?:key|password|secret|token|auth|api|pwd)[-_]?(?:key|password|secret|token|auth|api|pwd)?\s*"
    r"[:=]\s*['\"]([^'\"]{8,})['\"]"
)

_OPENAI_KEY_PATTERN: Final[str] = r"sk-[a-zA-Z0-9-]{32,}"
_AWS_KEY_PATTERN: Final[str] = r"AKIA[0-9A-Z]{16}"
_IP_PATTERN: Final[str] = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
_EMAIL_PATTERN: Final[str] = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"

_COMPILED_SECRETS: Final[List[re.Pattern]] = [
    re.compile(_OPENAI_KEY_PATTERN),
    re.compile(_AWS_KEY_PATTERN),
    re.compile(_IP_PATTERN),
    re.compile(_EMAIL_PATTERN),
]

_COMPILED_ASSIGNMENTS: Final[re.Pattern] = re.compile(_GENERIC_SECRET_PATTERN)


# ==============================================================================
# PRIVACY SANITIZER SERVICE
# ==============================================================================

class PrivacySanitizerService:
    """
    Application service responsible for PII and Secret redaction.
    """

    def __init__(self, user_context: IUserContext) -> None:
        """
        Initialize the service with an injected user context provider.

        Args:
            user_context: Implementation of the IUserContext port.
        """
        self._user_context = user_context

    # --------------------------------------------------------------------------
    # SECRET REDACTION LOGIC
    # --------------------------------------------------------------------------

    def sanitize(self, text: str) -> str:
        """Redact secrets and PII from a full string."""
        if not text:
            return ""
        line_iter = iter(text.splitlines(keepends=True))
        return "".join(list(self.sanitize_stream(line_iter)))

    def sanitize_stream(self, lines: Iterator[str]) -> Iterator[str]:
        """Process a text stream to redact sensitive patterns on-the-fly."""
        for line in lines:
            if not line.strip():
                yield line
                continue

            processed = line

            # 1. REDACT: Static hardcoded signatures
            for pattern in _COMPILED_SECRETS:
                processed = pattern.sub("[[REDACTED_SENSITIVE]]", processed)

            # 2. REDACT: Generic variable assignments
            processed = _COMPILED_ASSIGNMENTS.sub(
                lambda m: m.group(0).replace(m.group(1), "[[REDACTED_SECRET]]"),
                processed
            )
            yield processed

    # --------------------------------------------------------------------------
    # PATH ANONYMIZATION LOGIC
    # --------------------------------------------------------------------------

    def mask_paths(self, text: str) -> str:
        """Replace local filesystem paths with anonymous placeholders."""
        if not text:
            return ""
        line_iter = iter(text.splitlines(keepends=True))
        return "".join(list(self.mask_paths_stream(line_iter)))

    def mask_paths_stream(self, lines: Iterator[str]) -> Iterator[str]:
        """Process a text stream to mask local environment identifiers."""
        # 1. PREPARE: Retrieve OS metadata and compile dynamic patterns
        user_name = self._user_context.get_username()
        home_dir = self._user_context.get_home_directory()

        dynamic_patterns: List[Tuple[re.Pattern, str]] = []

        if home_dir:
            dynamic_patterns.append(
                (re.compile(re.escape(home_dir), re.IGNORECASE), "<USER_HOME>")
            )
        if user_name:
            # Matches username only when surrounded by path separators
            dynamic_patterns.append(
                (re.compile(rf"([\\/]){re.escape(user_name)}([\\/])"), r"\1<USER>\2")
            )

        # 2. PROCESS: Apply masking to each line
        for line in lines:
            # Force forward slashes to unify path style before replacement
            processed = line.replace("\\", "/")

            for pattern, replacement in dynamic_patterns:
                processed = pattern.sub(replacement, processed)

            yield processed


# ==============================================================================
# LEGACY COMPATIBILITY SHIMS
# ==============================================================================

def _get_default_service() -> PrivacySanitizerService:
    """Instantiate the service using the production infrastructure adapter."""
    from transcriptor4ai.infrastructure.system.user_context_adapter import UserContextAdapter
    return PrivacySanitizerService(UserContextAdapter())


def sanitize_text(text: str) -> str:
    """Legacy wrapper for PrivacySanitizerService.sanitize."""
    return _get_default_service().sanitize(text)


def sanitize_text_stream(lines: Iterator[str]) -> Iterator[str]:
    """Legacy wrapper for PrivacySanitizerService.sanitize_stream."""
    return _get_default_service().sanitize_stream(lines)


def mask_local_paths(text: str) -> str:
    """Legacy wrapper for PrivacySanitizerService.mask_paths."""
    return _get_default_service().mask_paths(text)


def mask_local_paths_stream(lines: Iterator[str]) -> Iterator[str]:
    """Legacy wrapper for PrivacySanitizerService.mask_paths_stream."""
    return _get_default_service().mask_paths_stream(lines)