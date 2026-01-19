from __future__ import annotations

"""
Heuristic Tokenization Strategy.

Implements a lightweight, character-based estimation algorithm used as 
the primary fallback when specialized libraries or APIs are unavailable.
"""

import math

from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

# Industry standard ratio for code/prose: approximately 4 characters per token
CHARS_PER_TOKEN_AVG: int = 4


class HeuristicStrategy(TokenizerStrategy):
    """
    Fallback algorithm using character density estimation.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Estimate tokens using the global characters-to-token ratio.

        Args:
            text: Raw input text to be measured.
            model_id: Model identifier (ignored in this heuristic approach).

        Returns:
            int: Total estimated tokens (minimum 0).
        """
        if not text:
            return 0

        # Strict character-to-token ceiling math to ensure consistency with tests
        return math.ceil(len(text) / CHARS_PER_TOKEN_AVG)