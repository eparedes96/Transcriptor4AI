from __future__ import annotations

"""
Unit tests for the Sanitizer module.

Verifies:
1. Redaction of API keys (OpenAI, AWS) and generic secrets.
2. Anonymization of network info (IPs, Emails).
3. Local path masking (User Home detection and replacement).
4. Resilience of user detection in restricted environments.
"""

import os
from pathlib import Path
from unittest.mock import patch

from transcriptor4ai.core.processing.sanitizer import (
    _get_user_info,
    mask_local_paths,
    sanitize_text,
)


# -----------------------------------------------------------------------------
# Secret Redaction Tests
# -----------------------------------------------------------------------------
def test_sanitize_text_redacts_provider_keys():
    """Ensure specific provider keys (OpenAI, AWS) are redacted."""
    openai_key = "sk-1234567890abcdef1234567890abcdef"
    aws_key = "AKIA1234567890ABCDEF"

    text = f"Connect using {openai_key} and {aws_key}."
    sanitized = sanitize_text(text)

    assert openai_key not in sanitized
    assert aws_key not in sanitized
    assert "[[REDACTED_SENSITIVE]]" in sanitized


def test_sanitize_text_redacts_assignments():
    """
    Verify that variable assignments for secrets are correctly masked
    using the generic pattern matcher.
    """
    cases = [
        ("PASSWORD = 'my_secret_pass'", "PASSWORD = '[[REDACTED_SECRET]]'"),
        ('db_token: "supersecret"', 'db_token: "[[REDACTED_SECRET]]"'),
        ("auth_key = '1234567890'", "auth_key = '[[REDACTED_SECRET]]'"),
    ]

    for raw, expected in cases:
        assert sanitize_text(raw) == expected


def test_sanitize_text_ignores_short_strings():
    """
    Ensure that short strings (potential false positives like 'true', 'dev')
    are not redacted.
    """
    text = "env = 'dev'"
    assert sanitize_text(text) == text


def test_sanitize_text_redacts_network_info():
    """Verify that IPs and emails are redacted."""
    text = "Contact user@example.com at 192.168.1.1"
    sanitized = sanitize_text(text)

    assert "user@example.com" not in sanitized
    assert "192.168.1.1" not in sanitized
    assert sanitized.count("[[REDACTED_SENSITIVE]]") == 2


# -----------------------------------------------------------------------------
# Path Masking Tests
# -----------------------------------------------------------------------------
def test_mask_local_paths_anonymizes_home_linux():
    """Verify that the home directory path is replaced by <USER_HOME> (Linux style)."""
    fake_home = "/home/testuser"
    text = f"Logs saved in {fake_home}/documents/project"

    _get_user_info.cache_clear()

    # Split patch calls to respect line length limits
    with patch("transcriptor4ai.core.processing.sanitizer.Path.home", return_value=Path(fake_home)):
        with patch(
            "transcriptor4ai.core.processing.sanitizer.os.getlogin",
            return_value="testuser"
        ):
            masked = mask_local_paths(text)
            assert fake_home not in masked
            assert "<USER_HOME>/documents/project" in masked


def test_mask_local_paths_anonymizes_home_windows():
    """Verify path masking works for Windows style backslashes."""
    fake_home = "C:/Users/testuser"
    text = "Path: C:/Users/testuser/Documents/Project"

    _get_user_info.cache_clear()

    # Simulate the bar normalization behavior
    with patch("transcriptor4ai.core.processing.sanitizer.Path.home", return_value=Path(fake_home)):
        with patch(
            "transcriptor4ai.core.processing.sanitizer.os.getlogin",
            return_value="testuser"
        ):
            masked = mask_local_paths(text)

            # El sanitizer convierte \ a / y luego aplica patrones.
            assert "testuser" not in masked
            assert "<USER_HOME>/Documents/Project" in masked


def test_mask_local_paths_anonymizes_standalone_username():
    """
    Verify that paths containing the username (outside home) are also masked.
    """
    text = "The file is at /var/lib/testuser/data.txt"

    _get_user_info.cache_clear()

    with patch("transcriptor4ai.core.processing.sanitizer.os.getlogin", return_value="testuser"):
        with patch(
            "transcriptor4ai.core.processing.sanitizer.Path.home",
            return_value=Path("/home/testuser")
        ):
            masked = mask_local_paths(text)

            assert "testuser" not in masked
            assert "/var/lib/<USER>/data.txt" in masked


# -----------------------------------------------------------------------------
# Robustness Tests
# -----------------------------------------------------------------------------
def test_get_user_info_fallback_logic():
    """
    Verify that _get_user_info doesn't crash if os.getlogin fails
    (common in CI/Docker environments without TTY).
    """
    _get_user_info.cache_clear()

    with patch("os.getlogin", side_effect=OSError("No TTY")):
        with patch.dict(os.environ, {"USER": "env_user", "USERNAME": "env_user"}):
            user, home = _get_user_info()
            assert user == "env_user"
            assert home is not None