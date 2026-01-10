from __future__ import annotations

"""
Unit tests for the Sanitizer utility.

Verifies the correct redaction of API keys, passwords, IPs, and emails,
as well as the anonymization of local system paths.
"""

import os
from pathlib import Path
from unittest.mock import patch
import pytest

from transcriptor4ai.utils.sanitizer import sanitize_text, mask_local_paths


# -----------------------------------------------------------------------------
# 1. Redaction Tests (Secrets & Sensitive Info)
# -----------------------------------------------------------------------------

def test_sanitize_text_redacts_provider_keys() -> None:
    """Ensure specific provider keys (OpenAI, AWS) are redacted."""
    openai_key = "sk-ant-api03-abcdefghijklmnopqrstuvwxyz012345"
    aws_key = "AKIA1234567890ABCDEF"

    text = f"Connect using {openai_key} and {aws_key}."
    sanitized = sanitize_text(text)

    assert openai_key not in sanitized
    assert aws_key not in sanitized
    assert "[[REDACTED_SENSITIVE]]" in sanitized


def test_sanitize_text_redacts_assignments() -> None:
    """Verify that variable assignments for secrets are correctly masked."""
    cases = [
        ("PASSWORD = 'my_secure_pass'", "PASSWORD = '[[REDACTED_SECRET]]'"),
        ("db_token: \"xyz-123-token-value\"", "db_token: \"[[REDACTED_SECRET]]\""),
        ("auth_key = 'very-long-sensitive-key'", "auth_key = '[[REDACTED_SECRET]]'"),
    ]

    for raw, expected in cases:
        assert sanitize_text(raw) == expected


def test_sanitize_text_ignores_short_strings() -> None:
    """Ensure that short strings (potential false positives) are not redacted."""
    text = "key = 'short'"
    assert sanitize_text(text) == text


def test_sanitize_text_redacts_network_info() -> None:
    """Verify that IPs and emails are redacted."""
    text = "Contact dev@company.com at 192.168.1.1"
    sanitized = sanitize_text(text)

    assert "dev@company.com" not in sanitized
    assert "192.168.1.1" not in sanitized
    assert sanitized.count("[[REDACTED_SENSITIVE]]") == 2


# -----------------------------------------------------------------------------
# 2. Path Masking Tests
# -----------------------------------------------------------------------------

def test_mask_local_paths_anonymizes_home() -> None:
    """Verify that the home directory path is replaced by <USER_HOME>."""
    fake_home = str(Path("/Users/testuser").absolute())
    text = f"Logs saved in {fake_home}/documents/project"

    with patch("transcriptor4ai.utils.sanitizer.Path.home", return_value=Path(fake_home)):
        with patch("transcriptor4ai.utils.sanitizer.os.getlogin", return_value="testuser"):
            masked = mask_local_paths(text)
            assert fake_home not in masked
            assert "<USER_HOME>/documents/project" in masked


def test_mask_local_paths_anonymizes_standalone_username() -> None:
    """Verify that username inside paths is masked."""
    text = "The file is at /home/testuser/data.txt"

    with patch("transcriptor4ai.utils.sanitizer.os.getlogin", return_value="testuser"):
        with patch("transcriptor4ai.utils.sanitizer.Path.home", return_value=Path("/home/testuser")):
            masked = mask_local_paths(text)
            assert "testuser" not in masked
            assert "/home/<USER_HOME>" in masked or "/home/<USER>" in masked