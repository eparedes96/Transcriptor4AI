from __future__ import annotations

"""
Unit tests for the Token Counter utility.
"""

from unittest.mock import patch
import pytest
from transcriptor4ai.core.processing.tokenizer import count_tokens, _count_heuristic

def test_token_counter_empty():
    assert count_tokens("") == 0
    assert count_tokens(None) == 0

def test_token_counter_heuristic_logic():
    """Verify strict math of heuristic (ceil(chars/4))."""
    # 4 chars -> 1 token
    assert _count_heuristic("abcd") == 1
    # 5 chars -> 2 tokens
    assert _count_heuristic("abcde") == 2
    # 10 chars -> 3 tokens
    assert _count_heuristic("1234567890") == 3

def test_fallback_when_tiktoken_missing():
    """Simulate ImportError for tiktoken and ensure fallback works."""
    with patch("transcriptor4ai.utils.token_counter.TIKTOKEN_AVAILABLE", False):
        text = "12345678"
        # Fallback: 8/4 = 2 tokens
        assert count_tokens(text) == 2

def test_tiktoken_integration():
    """
    If tiktoken IS installed in the test env, verify it returns int > 0.
    If not, skip.
    """
    try:
        import tiktoken
    except ImportError:
        pytest.skip("tiktoken not installed")

    text = "def main(): print('hello')"
    count = count_tokens(text, model="gpt-4o")
    assert count > 0
    assert isinstance(count, int)