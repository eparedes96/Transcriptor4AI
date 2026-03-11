from __future__ import annotations

import math

import pytest

from transcriptor4ai.application.processing.strategies.heuristic import HeuristicStrategy
from transcriptor4ai.application.processing.strategies.openai import TiktokenStrategy
from transcriptor4ai.application.processing.token_service import TokenizerService

# ==============================================================================
# TEST GROUP: TOKENIZER SERVICE ORCHESTRATION
# ==============================================================================

def test_should_return_zero_when_text_is_empty_or_none():
    """
    Ensures the service returns 0 for empty inputs without invoking any strategy.
    """
    # 1. ARRANGE
    service = TokenizerService()

    # 2. ACT
    res_empty = service.count("", "gpt-4o")
    res_none = service.count(None, "gpt-4o")  # type: ignore

    # 3. ASSERT
    assert res_empty == 0
    assert res_none == 0


def test_should_fallback_to_heuristic_when_tiktoken_is_unavailable(mocker):
    """
    Validates that the service defaults to HeuristicStrategy if the
    tiktoken library is not installed/available.
    """
    # 1. ARRANGE: Force tiktoken to be unavailable
    mocker.patch("transcriptor4ai.application.processing.token_service.TIKTOKEN_AVAILABLE", False)
    text = "Hello world, this is a test transcription."
    # Heuristic is ceil(len / 4) -> len is 41 -> 41/4 = 10.25 -> 11
    expected_count = math.ceil(len(text) / 4)
    service = TokenizerService()

    # 2. ACT
    count = service.count(text, "gpt-4o")

    # 3. ASSERT
    assert count == expected_count
    # Ensure tiktoken strategy was not even initialized
    assert service._tiktoken is None


def test_should_fallback_to_heuristic_if_tiktoken_proxy_fails(mocker):
    """
    Critical Resilience Test: If tiktoken is available but fails during execution
    (e.g., ValueError), the service must catch the error and return heuristic count.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.token_service.TIKTOKEN_AVAILABLE", True)
    mock_tiktoken = mocker.Mock()
    mock_tiktoken.count.side_effect = Exception("Tiktoken internal crash")

    service = TokenizerService()
    service._tiktoken = mock_tiktoken

    text = "Resilience test content"
    expected_heuristic = math.ceil(len(text) / 4)

    # 2. ACT
    count = service.count(text, "gpt-4o")

    # 3. ASSERT
    assert count == expected_heuristic
    mock_tiktoken.count.assert_called_once()


# ==============================================================================
# TEST GROUP: TIKTOKEN STRATEGY LOGIC
# ==============================================================================

@pytest.mark.parametrize("model_name, expected_encoding", [
    ("gpt-4o", "o200k_base"),
    ("gpt-4-turbo", "cl100k_base"),
    ("gpt-3.5-turbo", "cl100k_base"),
    ("legacy-model", "cl100k_base"),
    ("unknown-random-model", "o200k_base"),  # Default for modern
])
def test_tiktoken_strategy_selects_correct_encoding(mocker, model_name, expected_encoding):
    """
    Verifies that the TiktokenStrategy correctly maps model names to their
    respective BPE encodings.
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)
    mock_get_encoding = mocker.patch("tiktoken.get_encoding")
    strategy = TiktokenStrategy()
    text = "Test encoding selection"

    # 2. ACT
    strategy.count(text, model_name)

    # 3. ASSERT
    mock_get_encoding.assert_called_with(expected_encoding)


def test_tiktoken_strategy_handles_missing_encoding_with_fallback(mocker):
    """
    Ensures that if an encoding is not found in the local tiktoken registry,
    it falls back to 'cl100k_base' (the most common one).
    """
    # 1. ARRANGE
    mocker.patch("transcriptor4ai.application.processing.strategies.openai.TIKTOKEN_AVAILABLE", True)

    # First call fails, second succeeds
    mock_get = mocker.patch("tiktoken.get_encoding", side_effect=[
        ValueError("Encoding not found"),
        mocker.Mock(encode=lambda x, disallowed_special: [1, 2, 3])
    ])

    strategy = TiktokenStrategy()

    # 2. ACT
    count = strategy.count("any text", "rare-model")

    # 3. ASSERT
    assert count == 3
    assert mock_get.call_count == 2
    # Verify fallback call
    mock_get.assert_called_with("cl100k_base")


# ==============================================================================
# TEST GROUP: HEURISTIC STRATEGY
# ==============================================================================

def test_heuristic_strategy_math():
    """
    Simple verification of the 4:1 character-to-token ratio.
    """
    # 1. ARRANGE
    strategy = HeuristicStrategy()

    # 2. ACT & ASSERT
    assert strategy.count("1234", "any") == 1  # Exact 4 chars
    assert strategy.count("12345", "any") == 2  # 5 chars -> 1.25 -> 2 tokens
    assert strategy.count("a" * 100, "any") == 25  # 100 chars -> 25 tokens