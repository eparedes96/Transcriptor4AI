from __future__ import annotations

"""
Token counting utility for Transcriptor4AI (2026 Standard).

Provides token estimation for LLM contexts, aligned with the state of the art
as of Jan 2026 (GPT-5, Llama 4, Claude 4/5, Mistral Large 3).

Strategy:
1. Tiktoken (Exact): Prioritizes 'o200k_base' encoding (High efficiency).
2. Fallback Encodings: Drops to 'cl100k_base' if the newer one is missing.
3. Heuristic (Approx): Uses character density analysis (chars / 4) if no library.
"""

import logging
import math
from typing import Optional, Any

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Dependency Handling
# -----------------------------------------------------------------------------
TIKTOKEN_AVAILABLE = False
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    pass

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
# As of 2026, roughly 4 chars/token is still the standard safe heuristic
# for English code and text. Multilingual/dense code might be 3.5-3.8.
CHARS_PER_TOKEN = 4

# The standard encoding for GPT-4o, GPT-5, and compatible open models (Llama 4)
MODERN_ENCODING = "o200k_base"
LEGACY_ENCODING = "cl100k_base"

# Default fallback model if none provided
DEFAULT_MODEL = "gpt-5"


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate the number of tokens in a text string.

    Args:
        text: The content string to analyze.
        model: The target model name (e.g., "gpt-5", "claude-4", "llama-4").

    Returns:
        Integer count of tokens. Returns 0 for empty input.
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            return _count_with_tiktoken(text, model)
        except Exception as e:
            logger.debug(f"Tiktoken calculation failed: {e}. Falling back to heuristic.")

    return _count_heuristic(text)


def is_tiktoken_available() -> bool:
    """Return True if the exact counting library is installed."""
    return TIKTOKEN_AVAILABLE


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------
def _get_encoding(model_name: str) -> Any:
    """
    Retrieve the best available encoding object from tiktoken.
    Prioritizes model-specific, then modern generic, then legacy generic.
    """
    # 1. Try specific model name (e.g., "gpt-5-turbo")
    try:
        return tiktoken.encoding_for_model(model_name)
    except KeyError:
        pass

    # 2. Try Modern Encoding (GPT-4o/5 Standard)
    try:
        return tiktoken.get_encoding(MODERN_ENCODING)
    except ValueError:
        pass

    # 3. Try Legacy Encoding (GPT-4 Standard)
    try:
        return tiktoken.get_encoding(LEGACY_ENCODING)
    except ValueError:
        return tiktoken.get_encoding("p50k_base")


def _count_with_tiktoken(text: str, model: str) -> int:
    """
    Use tiktoken for precise counting.
    """
    encoding = _get_encoding(model)
    tokens = encoding.encode(text, disallowed_special=())
    return len(tokens)


def _count_heuristic(text: str) -> int:
    """
    Approximate tokens based on character count.

    Formula: ceil(len(text) / 4)
    This is a conservative estimate for most modern tokenizers (Tekken, Sentinel, o200k)
    which are generally more efficient than 4 chars/token, ensuring we don't
    underestimate the cost/size too significantly.
    """
    return math.ceil(len(text) / CHARS_PER_TOKEN)