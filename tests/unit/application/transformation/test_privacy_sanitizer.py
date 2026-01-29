from __future__ import annotations

# ==============================================================================
# TEST GROUP: PRIVACY SANITIZER SERVICE
# ==============================================================================

import pytest
from transcriptor4ai.application.transformation.privacy_sanitizer import PrivacySanitizerService


@pytest.fixture
def mock_user_context(mocker):
    """
    Creates a configurable mock for the UserContext Port.
    Default behavior mimics a standard Linux environment.
    """
    mock = mocker.Mock()
    mock.get_username.return_value = "testuser"
    mock.get_home_directory.return_value = "/home/testuser"
    return mock


@pytest.fixture
def sanitizer(mock_user_context) -> PrivacySanitizerService:
    """
    Injects the mock context into the service, bypassing OS calls.
    """
    return PrivacySanitizerService(mock_user_context)


@pytest.mark.unit
def test_sanitize_redacts_specific_provider_keys(sanitizer):
    """
    Verifies that known high-entropy patterns (OpenAI, AWS) are
    detected and redacted securely.
    """
    # 1. ARRANGE
    openai_key = "sk-7n9s8d7f6g5h4j3k2l1m0n9b8v7c6x5z4a3s2d1f"
    aws_key = "AKIA0987654321ABCDEF"
    text = f"Connect: {openai_key} | AWS: {aws_key}"

    # 2. ACT
    result = sanitizer.sanitize(text)

    # 3. ASSERT
    assert openai_key not in result
    assert aws_key not in result
    assert "[[REDACTED_SENSITIVE]]" in result


@pytest.mark.unit
def test_sanitize_redacts_generic_secret_assignments(sanitizer):
    """
    Verifies the heuristic logic that detects assignments of
    sensitive variables (passwords, tokens) regardless of language.
    """
    # 1. ARRANGE
    cases = [
        ('db_password = "SuperSecretPassword123"', 'db_password = "[[REDACTED_SECRET]]"'),
        ("api_token: 'abcdef1234567890'", "api_token: '[[REDACTED_SECRET]]'"),
        ("auth_key = 'x-live-12345678'", "auth_key = '[[REDACTED_SECRET]]'")
    ]

    for raw_input, expected in cases:
        # 2. ACT
        result = sanitizer.sanitize(raw_input)

        # 3. ASSERT
        assert result == expected


@pytest.mark.unit
def test_sanitize_ignores_false_positives(sanitizer):
    """
    Ensures that common, safe strings or short variable assignments
    are NOT flagged as secrets.
    """
    # 1. ARRANGE
    safe_text = (
        "env = 'production'\n"
        "timeout = '30s'\n"
        "public_key = 'short'\n"  # Too short to be a real secret
    )

    # 2. ACT
    result = sanitizer.sanitize(safe_text)

    # 3. ASSERT
    assert result == safe_text
    assert "[[REDACTED" not in result


@pytest.mark.unit
def test_sanitize_redacts_network_info(sanitizer):
    """
    Verifies redaction of PII like IP addresses and Emails.
    """
    # 1. ARRANGE
    text = "Server at 192.168.1.50, contact admin@corp.com"

    # 2. ACT
    result = sanitizer.sanitize(text)

    # 3. ASSERT
    assert "192.168.1.50" not in result
    assert "admin@corp.com" not in result
    assert result.count("[[REDACTED_SENSITIVE]]") == 2


@pytest.mark.unit
def test_mask_paths_uses_injected_context_linux(sanitizer, mock_user_context):
    """
    Simulates a Unix environment via the Port Mock and verifies
    path anonymization.
    """
    # 1. ARRANGE: Configure mock for Linux
    mock_user_context.get_home_directory.return_value = "/home/dev"
    mock_user_context.get_username.return_value = "dev"

    input_text = "Logs located at /home/dev/projects/app.log"

    # 2. ACT
    result = sanitizer.mask_paths(input_text)

    # 3. ASSERT
    assert "/home/dev" not in result
    assert "<USER_HOME>/projects/app.log" in result


@pytest.mark.unit
def test_mask_paths_uses_injected_context_windows(sanitizer, mock_user_context):
    """
    Simulates a Windows environment via the Port Mock.
    Crucial for verifying cross-platform logic without needing a Windows runner.
    """
    # 1. ARRANGE: Configure mock for Windows
    mock_user_context.get_home_directory.return_value = r"C:\Users\Admin"
    mock_user_context.get_username.return_value = "Admin"

    # Input uses Windows backslashes
    input_text = r"Error in C:\Users\Admin\Documents\secret.txt"

    # 2. ACT
    result = sanitizer.mask_paths(input_text)

    # 3. ASSERT
    # The sanitizer usually normalizes to forward slashes for Regex simplicity
    assert "Admin" not in result
    assert "<USER_HOME>/Documents/secret.txt" in result


@pytest.mark.unit
def test_mask_paths_resilience_to_missing_context(sanitizer, mock_user_context):
    """
    Verifies fail-safe behavior: If OS context cannot be resolved (None),
    the sanitizer should return the text unaltered instead of crashing.
    """
    # 1. ARRANGE
    mock_user_context.get_home_directory.return_value = None
    mock_user_context.get_username.return_value = None

    text = "Path /usr/bin/python"

    # 2. ACT
    result = sanitizer.mask_paths(text)

    # 3. ASSERT
    assert result == text


@pytest.mark.unit
def test_sanitize_stream_consistency(sanitizer):
    """
    Validates that the streaming implementation produces identical
    results to the full-string method.
    """
    # 1. ARRANGE
    lines = [
        "API_KEY = '1234567890abcdef'\n",
        "print('clean')\n"
    ]
    iterator = iter(lines)

    # 2. ACT
    stream_result = list(sanitizer.sanitize_stream(iterator))
    joined_result = "".join(stream_result)

    # 3. ASSERT
    assert "[[REDACTED_SECRET]]" in joined_result
    assert "clean" in joined_result
    assert len(stream_result) == 2