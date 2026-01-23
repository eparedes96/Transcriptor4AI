from __future__ import annotations

"""
Base Definitions for Tokenization Strategies.

Provides the abstract interface and common domain constants for the 
strategy-based token counting system.
"""

from abc import ABC, abstractmethod

# Global constant for fallback or uninitialized model selection
DEFAULT_MODEL: str = "- Default Model -"


class TokenizerStrategy(ABC):
    """
    Abstract base class for model-specific tokenization algorithms.
    """

    @abstractmethod
    def count(self, text: str, model_id: str) -> int:
        """
        Calculate the token count for a given text segment.

        Args:
            text: Input string to be tokenized.
            model_id: Specific model identifier for encoding selection.

        Returns:
            int: Total token count.
        """
        pass