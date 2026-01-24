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

from transcriptor4ai.application.processing.strategies import (
    DEFAULT_MODEL,
    TIKTOKEN_AVAILABLE,
    HeuristicStrategy,
    TiktokenStrategy
)

# Standard logger initialization
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

        Args:
            text: Raw input text to tokenize.
            model: Target model identifier.

        Returns:
            int: Calculated or estimated token count.
        """
        # 1. VALIDATION: Handle empty or null inputs early
        if not text:
            return 0

        # 2. PROXY EXECUTION: High-Fidelity Local Path
        # tiktoken (o200k/cl100k) is used as a proxy for almost all modern text LLMs
        # because densities for Llama, Mistral, and Qwen are structurally similar.
        if TIKTOKEN_AVAILABLE and self._tiktoken:
            try:
                # Force proxy counting to avoid remote API calls
                return self._tiktoken.count(text, model)
            except Exception as e:
                logger.debug(f"BPE Proxy failed for '{model}': {e}. Falling back.")

        # 3. FALLBACK: Absolute char-based density estimation
        return self._heuristic.count(text, model)


# ==============================================================================
# PUBLIC API (SINGLETON ACCESS)
# ==============================================================================

# Internal service instance for global application use
_SERVICE_INSTANCE = TokenizerService()


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate tokens for any discovered model using the local proxy strategy.

    Args:
        text: Input string content.
        model: Target model name (e.g., 'gpt-4o', 'claude-3-5-sonnet').

    Returns:
        int: Total token count.
    """
    return _SERVICE_INSTANCE.count(text, model)


def is_tiktoken_available() -> bool:
    """
    Check if the high-precision local engine is operational.

    Returns:
        bool: True if tiktoken is successfully imported and ready.
    """
    return TIKTOKEN_AVAILABLE