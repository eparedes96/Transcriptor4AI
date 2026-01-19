from __future__ import annotations

"""
Unit tests for individual Tokenizer Strategies.

Verifies the integration with provider-specific SDKs (OpenAI, Anthropic, Google, 
Mistral, HF) using extensive mocking to ensure tests are isolated, 
deterministic, and do not require active network connections.
"""

from unittest.mock import MagicMock, patch
import pytest

from transcriptor4ai.core.processing.strategies.heuristic import HeuristicStrategy
from transcriptor4ai.core.processing.strategies.openai import TiktokenStrategy
from transcriptor4ai.core.processing.strategies.anthropic import AnthropicApiStrategy
from transcriptor4ai.core.processing.strategies.google import GoogleApiStrategy
from transcriptor4ai.core.processing.strategies.local import MistralStrategy, TransformersStrategy


def test_heuristic_strategy_math() -> None:
    """Verify the character-to-token ratio logic (1 token approx 4 chars)."""
    strategy = HeuristicStrategy()
    # 8 chars -> 2 tokens
    assert strategy.count("12345678", "any") == 2
    # 9 chars -> 3 tokens (ceil)
    assert strategy.count("123456789", "any") == 3


@patch("transcriptor4ai.core.processing.strategies.openai.tiktoken")
def test_tiktoken_strategy_encoding(mock_tiktoken: MagicMock) -> None:
    """Verify Tiktoken strategy calls the correct encoding for OpenAI models."""
    mock_encoding = MagicMock()
    mock_encoding.encode.return_value = [1, 2, 3]  # 3 tokens
    mock_tiktoken.get_encoding.return_value = mock_encoding

    strategy = TiktokenStrategy()
    count = strategy.count("sample text", "gpt-4o")

    assert count == 3
    mock_tiktoken.get_encoding.assert_called_with("o200k_base")


@patch("transcriptor4ai.core.processing.strategies.anthropic.anthropic")
@patch.dict("os.environ", {"ANTHROPIC_API_KEY": "sk-test-key"})
def test_anthropic_strategy_api(mock_anthropic: MagicMock) -> None:
    """Verify Anthropic strategy maps models and extracts input_tokens from response."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.input_tokens = 42
    mock_client.beta.messages.count_tokens.return_value = mock_response
    mock_anthropic.Anthropic.return_value = mock_client

    strategy = AnthropicApiStrategy()
    count = strategy.count("hello claude", "claude-3-5-sonnet")

    assert count == 42
    mock_client.beta.messages.count_tokens.assert_called()


@patch("transcriptor4ai.core.processing.strategies.google.genai", create=True)
@patch.dict("os.environ", {"GOOGLE_API_KEY": "ai-test-key"})
def test_google_strategy_api(mock_genai: MagicMock) -> None:
    """Verify Google strategy utilizes the GenAI client correctly."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.total_token_count = 10
    mock_client.models.count_tokens.return_value = mock_response
    mock_genai.Client.return_value = mock_client

    strategy = GoogleApiStrategy()
    count = strategy.count("hello gemini", "gemini-1.5-pro")

    assert count == 10
    mock_client.models.count_tokens.assert_called_with(
        model="gemini-1.5-pro",
        contents="hello gemini"
    )


@patch("transcriptor4ai.core.processing.strategies.local.MistralTokenizer")
def test_mistral_strategy_local(mock_tokenizer_cls: MagicMock) -> None:
    """Verify Mistral strategy calls the local Tekken tokenizer."""
    mock_tokenizer = MagicMock()
    mock_encoded = MagicMock()
    mock_encoded.tokens = [0, 0, 0, 0, 0]  # 5 tokens
    mock_tokenizer.encode_chat_completion.return_value = mock_encoded
    mock_tokenizer_cls.v3.return_value = mock_tokenizer

    strategy = MistralStrategy()
    count = strategy.count("code test", "codestral")

    assert count == 5
    mock_tokenizer_cls.v3.assert_called_once()