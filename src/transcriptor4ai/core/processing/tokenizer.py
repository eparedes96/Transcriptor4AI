from __future__ import annotations

"""
Token Counting Utility.

Provides token estimation for LLM contexts (GPT, Claude, etc.).
Uses 'tiktoken' if available for accurate counting, falling back to
heuristic character density analysis otherwise.
"""

import logging
import math
from typing import Optional

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
# Heuristics
CHARS_PER_TOKEN_AVG = 4

# Encodings
MODERN_ENCODING = "o200k_base"  # GPT-4o, GPT-5
LEGACY_ENCODING = "cl100k_base"  # GPT-4, GPT-3.5

# Multipliers relative to o200k_base (Approximations for other models)
CLAUDE_FACTOR = 1.05
GEMINI_FACTOR = 1.0

# Default
DEFAULT_MODEL = "GPT-4o / GPT-5"


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate the number of tokens in a text string.

    Adapts the counting strategy based on the target model model family.

    Args:
        text: The input text.
        model: The target model name (e.g., "Claude 3.5").

    Returns:
        int: The estimated token count.
    """
    if not text:
        return 0

    model_lower = (model or "").lower()

    if TIKTOKEN_AVAILABLE:
        try:
            # 1. Determine Encoding Base
            encoding_name = MODERN_ENCODING
            if "legacy" in model_lower or "gpt-3.5" in model_lower or "gpt-4 " in model_lower:
                encoding_name = LEGACY_ENCODING

            # 2. Count Base Tokens
            base_count = _count_with_encoding(text, encoding_name)

            # 3. Apply Correction Factors for non-native models
            if "claude" in model_lower:
                return int(base_count * CLAUDE_FACTOR)

            # Llama/Gemini/GPT use base count
            return base_count

        except Exception as e:
            logger.debug(f"Tiktoken calculation failed: {e}. Falling back to heuristic.")

    # 4. Fallback Heuristic
    return _count_heuristic(text)


def is_tiktoken_available() -> bool:
    """
    Check if the accurate counting library is available.

    Returns:
        bool: True if tiktoken is installed.
    """
    return TIKTOKEN_AVAILABLE


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------
def _count_with_encoding(text: str, encoding_name: str) -> int:
    """Count tokens using specific tiktoken encoding."""
    try:
        encoding = tiktoken.get_encoding(encoding_name)
    except ValueError:
        encoding = tiktoken.get_encoding("cl100k_base")

    tokens = encoding.encode(text, disallowed_special=())
    return len(tokens)


def _count_heuristic(text: str) -> int:
    """
    Approximate tokens using character density.
    Standard approximation: 4 characters ~= 1 token.
    """
    return math.ceil(len(text) / CHARS_PER_TOKEN_AVG)