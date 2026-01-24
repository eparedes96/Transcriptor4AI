from __future__ import annotations

"""
Heuristic Tokenization Strategy.
"""

import math

# Use explicit relative import from the local base module
from .base import TokenizerStrategy

# ==============================================================================
# HEURISTIC IMPLEMENTATION
# ==============================================================================
class HeuristicStrategy(TokenizerStrategy):
    """
    Fallback algorithm using character density estimation.
    """

    def count(self, text: str, model_id: str) -> int:
        """Estimate tokens using the global characters-to-token ratio."""
        if not text:
            return 0

        # Industry standard: ~4 chars per token
        return math.ceil(len(text) / 4)