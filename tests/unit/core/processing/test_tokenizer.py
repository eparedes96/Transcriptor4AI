from __future__ import annotations

"""
Unit tests for the Tokenizer Service (Orchestrator).

Verifies the Strategy Pattern implementation:
1. Correct mapping between model names and execution strategies.
2. Resilience through the heuristic fallback mechanism.
3. Proper handling of default model placeholders.
"""

from unittest.mock import MagicMock, patch
import pytest

from transcriptor4ai.core.processing.tokenizer import TokenizerService, count_tokens


@pytest.fixture
def service() -> TokenizerService:
    """Provide a fresh instance of the TokenizerService."""
    return TokenizerService()


def test_tokenizer_service_mapping(service: TokenizerService) -> None:
    """Verify that specific model keywords route to the correct strategies."""
    # Test internal mapping through protected attribute access for validation
    with patch.object(service._strategy_map["gpt"], "count", return_value=10):
        assert service.count("text", "gpt-4") == 10

    with patch.object(service._strategy_map["claude"], "count", return_value=20):
        assert service.count("text", "claude-3") == 20

    with patch.object(service._strategy_map["gemini"], "count", return_value=30):
        assert service.count("text", "gemini-pro") == 30


def test_tokenizer_service_fallback_on_failure(service: TokenizerService) -> None:
    """Ensure that if a strategy fails (e.g. API Error), the heuristic takes over."""
    # Mocking GPT strategy to raise an exception
    with patch.object(service._strategy_map["gpt"], "count", side_effect=Exception("API Down")):
        # "12345678" -> 8 chars -> Heuristic should return 2
        count = service.count("12345678", "gpt-4")
        assert count == 2


def test_tokenizer_service_default_model_handling(service: TokenizerService) -> None:
    """Verify that the '- Default Model -' string triggers Tiktoken/GPT logic."""
    with patch("transcriptor4ai.core.processing.strategies.openai.TiktokenStrategy.count") as mock_tik:
        mock_tik.return_value = 100
        count = service.count("some text", "- Default Model -")
        assert count == 100


def test_public_count_tokens_interface() -> None:
    """Verify the singleton-based public function works as expected."""
    with patch("transcriptor4ai.core.processing.tokenizer._SERVICE_INSTANCE.count") as mock_service:
        mock_service.return_value = 5
        assert count_tokens("hello") == 5
        mock_service.assert_called_once()