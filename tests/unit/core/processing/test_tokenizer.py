from __future__ import annotations

"""
Unit tests for the Token Counter utility.

Verifies the hybrid counting engine logic, including specialized 
strategy selection, tiktoken integration, and heuristic fallback 
reliability.
"""

from unittest.mock import patch

import pytest

from transcriptor4ai.core.processing.strategies.heuristic import HeuristicStrategy
from transcriptor4ai.core.processing.tokenizer import count_tokens


# ==============================================================================
# TOKENIZER UNIT TESTS
# ==============================================================================

def test_token_counter_empty() -> None:
    """Empty input should return 0 tokens."""
    assert count_tokens("") == 0


def test_token_counter_heuristic_math() -> None:
    """
    Verify strict math of heuristic (ceil(chars/4)).

    Used as the primary fallback when dependencies or APIs are missing.
    """
    strategy = HeuristicStrategy()
    # Model ID arg is unused in heuristic but required by the Strategy interface
    assert strategy.count("abcd", "mock_model") == 1
    assert strategy.count("abcde", "mock_model") == 2
    assert strategy.count("1234567890", "mock_model") == 3


def test_fallback_when_tiktoken_missing() -> None:
    """
    Simulate ImportError for tiktoken and ensure the heuristic is used.
    """
    target_path = "transcriptor4ai.core.processing.strategies.openai.TIKTOKEN_AVAILABLE"
    with patch(target_path, False):
        text = "12345678"
        assert count_tokens(text) == 2


def test_tiktoken_integration_gpt() -> None:
    """
    Verify live tiktoken integration for GPT models if the library is present.

    Skips execution in environments where tiktoken is not installed to
    prevent false negatives in headless CI pipelines.
    """
    try:
        import tiktoken
    except ImportError:
        pytest.skip("tiktoken not installed in current test environment")

    text = "def main(): print('hello')"
    count = count_tokens(text, model="GPT-4o")

    # Accurate BPE count should always be a positive integer
    assert count > 0
    assert isinstance(count, int)