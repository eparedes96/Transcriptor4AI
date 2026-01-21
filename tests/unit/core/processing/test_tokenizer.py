from __future__ import annotations

"""
Unit tests for the Tokenizer Service (Universal Proxy).

Verifies the BPE Proxy implementation:
1. Correct delegation to tiktoken when available.
2. Robust fallback to heuristic estimation on failure or absence.
3. Precise handling of empty inputs and the public API singleton.
"""

from unittest.mock import patch

import pytest

from transcriptor4ai.core.processing.tokenizer import TokenizerService, count_tokens


@pytest.fixture
def service() -> TokenizerService:
    """Provide a fresh instance of the TokenizerService."""
    return TokenizerService()


def test_tokenizer_service_proxy_delegation(service: TokenizerService) -> None:
    """Verify that any model routes through the BPE Proxy (tiktoken)."""
    # We mock the internal tiktoken strategy which is now the universal proxy
    with patch.object(service, "_tiktoken") as mock_tik:
        mock_tik.count.return_value = 42

        # Any model (OpenAI, Claude, Llama) should use the proxy
        assert service.count("some text", "gpt-4o") == 42
        assert service.count("some text", "claude-3-sonnet") == 42
        assert service.count("some text", "llama-3-70b") == 42


def test_tokenizer_service_fallback_on_proxy_failure(service: TokenizerService) -> None:
    """Ensure that if the BPE Proxy fails, the heuristic takes over silently."""
    # Simulate a failure in the high-precision proxy
    with patch.object(service, "_tiktoken") as mock_tik:
        mock_tik.count.side_effect = Exception("Library Error")

        # "12345678" -> 8 chars -> Heuristic (8/4) should return 2
        count = service.count("12345678", "any-model")
        assert count == 2


def test_tokenizer_service_heuristic_fallback_when_no_tiktoken(service: TokenizerService) -> None:
    """Verify fallback when tiktoken is not installed or initialized."""
    service._tiktoken = None

    # 12 chars -> 3 tokens
    assert service.count("123456789012", "any-model") == 3


def test_tokenizer_service_empty_input(service: TokenizerService) -> None:
    """Verify that empty or None inputs return zero tokens."""
    assert service.count("", "gpt-4o") == 0
    assert service.count(None, "gpt-4o") == 0  # type: ignore


def test_public_count_tokens_interface() -> None:
    """Verify the singleton-based public function delegates to the service."""
    target = "transcriptor4ai.core.processing.tokenizer._SERVICE_INSTANCE.count"
    with patch(target) as mock_count:
        mock_count.return_value = 99
        assert count_tokens("hello world", "model-x") == 99
        mock_count.assert_called_once_with("hello world", "model-x")