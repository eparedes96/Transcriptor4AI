from __future__ import annotations

"""
Heuristic Tokenization Strategy.

Implements a lightweight, character-based estimation algorithm used as 
the primary fallback when specialized libraries or APIs are unavailable.
"""

import math

from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

# Industry standard ratio for English/Code: approx 4 characters per token
CHARS_PER_TOKEN_AVG: int = 4


class HeuristicStrategy(TokenizerStrategy):
    """
    Fallback algorithm using character density estimation.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Estimate tokens using the global characters-to-token ratio.

        Args:
            text: Raw input text.
            model_id: Identifier (ignored in this heuristic approach).

        Returns:
            int: Ceiling of the character count divided by the average ratio.
        """
        if not text:
            return 0
        return math.ceil(len(text) / CHARS_PER_TOKEN_AVG)