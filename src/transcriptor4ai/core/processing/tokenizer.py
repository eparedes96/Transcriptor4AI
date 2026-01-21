from __future__ import annotations

"""
Universal Token Counting Engine (BPE Proxy).

Provides high-precision token estimation for LLM contexts using a 
'Universal Proxy' strategy. Prioritizes local BPE encoding (tiktoken) 
for all modern architectures to ensure accuracy and eliminate API Key 
dependencies. Falls back to a refined heuristic only if local libraries 
are unavailable.
"""

import logging

from transcriptor4ai.core.processing.strategies.base import DEFAULT_MODEL
from transcriptor4ai.core.processing.strategies.heuristic import HeuristicStrategy
from transcriptor4ai.core.processing.strategies.openai import TIKTOKEN_AVAILABLE, TiktokenStrategy

logger = logging.getLogger(__name__)


# ==============================================================================
# UNIVERSAL TOKENIZER SERVICE
# ==============================================================================

class TokenizerService:
    """
    Centralized service for provider-agnostic token estimation.

    Implements a proxy logic where tiktoken (OpenAI BPE) acts as the
    high-fidelity estimator for most modern models, ensuring a zero-interruption
    UX without requiring remote API keys.
    """

    def __init__(self) -> None:
        """Initialize the service with local strategies and heuristic fallback."""
        self._heuristic = HeuristicStrategy()
        self._tiktoken = TiktokenStrategy() if TIKTOKEN_AVAILABLE else None

    def count(self, text: str, model: str) -> int:
        """
        Calculate token count using the Universal BPE Proxy.

        Prioritizes the most accurate local method available.
        1. Local BPE Proxy (tiktoken) -> High Precision (Matches or ~95% proxy).
        2. Heuristic (chars/4) -> Fallback.

        Args:
            text: Raw input text to tokenize.
            model: Target model identifier.

        Returns:
            int: Calculated or estimated token count.
        """
        if not text:
            return 0

        # High-Fidelity Local Path (Proxy for almost all modern text LLMs)
        if TIKTOKEN_AVAILABLE and self._tiktoken:
            try:
                # We use tiktoken as a universal proxy.
                # Modern models (Llama, Mistral, Qwen) share similar densities.
                return self._tiktoken.count(text, model)
            except Exception as e:
                logger.debug(f"BPE Proxy failed for '{model}': {e}. Using heuristic.")

        # Absolute Fallback (No libraries or unexpected error)
        return self._heuristic.count(text, model)


# ==============================================================================
# PUBLIC API
# ==============================================================================

# Singleton instance for global application access
_SERVICE_INSTANCE = TokenizerService()


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate tokens for any discovered model using the local proxy strategy.

    Args:
        text: Input string content.
        model: Target model name.

    Returns:
        int: Total token count.
    """
    return _SERVICE_INSTANCE.count(text, model)


def is_tiktoken_available() -> bool:
    """
    Check if the high-precision local engine is operational.

    Returns:
        bool: True if tiktoken is successfully imported.
    """
    return TIKTOKEN_AVAILABLE