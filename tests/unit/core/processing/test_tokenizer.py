from __future__ import annotations

"""
Unit tests for the Token Counter utility.

Verifies:
1. Heuristic fallback logic (when tiktoken is missing).
2. Tiktoken integration (when available).
"""

from unittest.mock import patch
import pytest
from transcriptor4ai.core.processing.tokenizer import count_tokens
from transcriptor4ai.core.processing.strategies.heuristic import HeuristicStrategy


def test_token_counter_empty():
    """Empty input should return 0 tokens."""
    assert count_tokens("") == 0


def test_token_counter_heuristic_math():
    """
    Verify strict math of heuristic (ceil(chars/4)).
    Used as fallback when dependencies are missing.
    """
    strategy = HeuristicStrategy()
    # Model ID arg is unused in heuristic but required by interface
    assert strategy.count("abcd", "mock_model") == 1
    assert strategy.count("abcde", "mock_model") == 2
    assert strategy.count("1234567890", "mock_model") == 3


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