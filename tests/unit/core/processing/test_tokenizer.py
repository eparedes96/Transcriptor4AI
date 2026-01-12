from __future__ import annotations

"""
Unit tests for the Token Counter utility.

Verifies:
1. Heuristic fallback logic (when tiktoken is missing).
2. Tiktoken integration (when available).
3. Model-specific adjustments (e.g., Claude multipliers).
"""

from unittest.mock import patch
import pytest
from transcriptor4ai.core.processing.tokenizer import count_tokens, _count_heuristic


def test_token_counter_empty():
    """Empty input should return 0 tokens."""
    assert count_tokens("") == 0



def test_token_counter_heuristic_math():
    """
    Verify strict math of heuristic (ceil(chars/4)).
    Used as fallback when dependencies are missing.
    """
    assert _count_heuristic("abcd") == 1
    assert _count_heuristic("abcde") == 2
    assert _count_heuristic("1234567890") == 3


def test_fallback_when_tiktoken_missing():
    """
    Simulate ImportError for tiktoken and ensure the heuristic is used.
    """
    with patch("transcriptor4ai.core.processing.tokenizer.TIKTOKEN_AVAILABLE", False):
        text = "12345678"
        assert count_tokens(text) == 2


def test_tiktoken_integration_gpt():
    """
    If tiktoken IS installed in the test env, verify it returns int > 0.
    If not installed, we skip this test to avoid false negatives in CI.
    """
    try:
        import tiktoken
    except ImportError:
        pytest.skip("tiktoken not installed in test environment")

    text = "def main(): print('hello')"
    count = count_tokens(text, model="GPT-4o")

    assert count > 0
    assert isinstance(count, int)


def test_token_counter_claude_multiplier():
    """
    Verify that selecting a Claude model applies the safety multiplier.
    We mock _count_with_encoding to return a fixed value.
    """
    with patch("transcriptor4ai.core.processing.tokenizer.TIKTOKEN_AVAILABLE", True):
        with patch("transcriptor4ai.core.processing.tokenizer._count_with_encoding", return_value=100):
            gpt_count = count_tokens("text", model="GPT-4")
            assert gpt_count == 100

            claude_count = count_tokens("text", model="Claude 3.5")
            assert claude_count == 105