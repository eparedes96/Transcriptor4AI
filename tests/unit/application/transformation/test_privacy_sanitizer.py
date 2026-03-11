from __future__ import annotations

# ==============================================================================
# TEST GROUP: PRIVACY SANITIZER SERVICE (UNIT)
# ==============================================================================
import pytest

from transcriptor4ai.application.transformation.privacy_sanitizer import PrivacySanitizerService


@pytest.fixture
def mock_user_context(mocker):
    """
    Creates a configurable mock for the UserContext Port.
    Simulates a standard developer environment to provide ground truth for redaction.
    """
    mock = mocker.Mock()
    mock.get_username.return_value = "testuser"
    mock.get_home_directory.return_value = "/home/testuser"
    return mock


@pytest.fixture
def sanitizer(mock_user_context) -> PrivacySanitizerService:
    """
    Injects the mock context into the service, bypassing real OS calls.
    """
    return PrivacySanitizerService(mock_user_context)


# ------------------------------------------------------------------------------
# SCENARIO: SECRET REDACTION (REGEX ENGINE)
# ------------------------------------------------------------------------------

def test_sanitize_should_redact_high_entropy_provider_keys(sanitizer):
    """
    Ensures that known API key patterns (OpenAI, AWS) are detected
    and replaced by a generic sensitive tag.
    """
    # 1. ARRANGE
    openai_key = "sk-7n9s8d7f6g5h4j3k2l1m0n9b8v7c6x5z4a3s2d1f"
    aws_key = "AKIA0987654321ABCDEF"
    text = f"CRITICAL: key={openai_key}, access={aws_key}"

    # 2. ACT
    result = sanitizer.sanitize(text)

    # 3. ASSERT
    assert openai_key not in result
    assert aws_key not in result
    assert "[[REDACTED_SENSITIVE]]" in result


@pytest.mark.parametrize("assignment, expected", [
    ('db_password = "SuperSecretPassword123"', 'db_password = "[[REDACTED_SECRET]]"'),
    ("api_token: 'abcdef1234567890'", "api_token: '[[REDACTED_SECRET]]'"),
    ("auth_key = 'x-live-12345678'", "auth_key = '[[REDACTED_SECRET]]'"),
    ("PWD: \"MyHiddenPassword\"", "PWD: \"[[REDACTED_SECRET]]\""),
])
def test_sanitize_should_redact_generic_secret_assignments(sanitizer, assignment, expected):
    """
    Validates the heuristic assignment detection for various naming
    conventions and languages.
    """
    # 2. ACT
    result = sanitizer.sanitize(assignment)

    # 3. ASSERT
    assert result == expected


def test_sanitize_should_ignore_short_or_safe_assignments(sanitizer):
    """
    Prevents over-redaction (False Positives) on common non-sensitive assignments.
    """
    # 1. ARRANGE
    safe_text = "env='prod'\ntimeout=30\npublic_key='short'"

    # 2. ACT
    result = sanitizer.sanitize(safe_text)

    # 3. ASSERT
    assert result == safe_text
    assert "[[REDACTED" not in result


def test_sanitize_should_redact_network_identifiers(sanitizer):
    """
    Verifies that IP addresses and Emails (PII) are masked to prevent identity leaks.
    """
    # 1. ARRANGE
    text = "Inbound from 192.168.1.1, contact: support@transcriptor.ai"

    # 2. ACT
    result = sanitizer.sanitize(text)

    # 3. ASSERT
    assert "192.168.1.1" not in result
    assert "support@transcriptor.ai" not in result
    assert result.count("[[REDACTED_SENSITIVE]]") == 2


# ------------------------------------------------------------------------------
# SCENARIO: PATH MASKING (ENVIRONMENT AWARENESS)
# ------------------------------------------------------------------------------

def test_mask_paths_should_anonymize_injected_linux_context(sanitizer, mock_user_context):
    """
    Simulates a Linux environment and verifies that local paths are
    transformed into platform-agnostic tags.
    """
    # 1. ARRANGE
    mock_user_context.get_home_directory.return_value = "/home/dev"
    mock_user_context.get_username.return_value = "dev"
    input_text = "Config saved in /home/dev/workspace/app.json"

    # 2. ACT
    result = sanitizer.mask_paths(input_text)

    # 3. ASSERT
    assert "/home/dev" not in result
    assert "<USER_HOME>/workspace/app.json" in result


def test_mask_paths_should_anonymize_injected_windows_context(sanitizer, mock_user_context):
    """
    Ensures Windows-style backslashes are handled and normalized during masking.
    """
    # 1. ARRANGE
    mock_user_context.get_home_directory.return_value = r"C:\Users\Admin"
    mock_user_context.get_username.return_value = "Admin"
    input_text = r"Error at C:\Users\Admin\AppData\Local\Temp\log.txt"

    # 2. ACT
    result = sanitizer.mask_paths(input_text)

    # 3. ASSERT
    assert "Admin" not in result
    # Sanitizer normalizes to forward slashes internally for consistency
    assert "<USER_HOME>/AppData/Local/Temp/log.txt" in result


def test_mask_paths_with_real_deeply_nested_asset(sanitizer, mock_user_context, static_assets_path):
    """
    EDGE CASE: Validates that even deeply nested real paths from the project
    data are masked if they are passed as text.
    """
    # 1. ARRANGE
    real_file_path = static_assets_path / "edge_cases" / "deeply_nested" / "level_1" / "level_2" / "level_3" / "level_4" / "deep_file.txt"

    # We simulate that the 'static_assets_path' is actually part of the user's home
    home_path = str(static_assets_path.parent)
    mock_user_context.get_home_directory.return_value = home_path

    input_text = f"Processing physical file: {real_file_path}"

    # 2. ACT
    result = sanitizer.mask_paths(input_text)

    # 3. ASSERT
    assert home_path not in result
    assert "<USER_HOME>/data/edge_cases/deeply_nested" in result.replace("\\", "/")


def test_mask_paths_should_fail_safely_when_context_is_missing(sanitizer, mock_user_context):
    """
    Ensures the application doesn't crash if OS identity cannot be
    resolved; it should return the original text.
    """
    # 1. ARRANGE
    mock_user_context.get_home_directory.return_value = None
    mock_user_context.get_username.return_value = None
    text = "System path: /etc/hosts"

    # 2. ACT
    result = sanitizer.mask_paths(text)

    # 3. ASSERT
    assert result == text


# ------------------------------------------------------------------------------
# SCENARIO: STREAMING INTEGRITY
# ------------------------------------------------------------------------------

def test_sanitize_stream_should_match_string_logic(sanitizer):
    """
    Verifies that the streaming (generator) implementation maintains
    semantic parity with the full-string method.
    """
    # 1. ARRANGE
    lines = [
        "SECRET_KEY = 'secret_val_12345'\n",
        "DEBUG_LOG: User john_doe connected.\n"
    ]
    iterator = iter(lines)

    # 2. ACT
    stream_result = list(sanitizer.sanitize_stream(iterator))
    joined_result = "".join(stream_result)

    # 3. ASSERT
    assert "[[REDACTED_SECRET]]" in joined_result
    assert "john_doe" in joined_result
    assert len(stream_result) == 2