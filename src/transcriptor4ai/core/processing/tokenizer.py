from __future__ import annotations

"""
Hybrid Token Counting Engine.

Provides high-precision token estimation for Large Language Model (LLM) 
contexts. Implements a Strategy Pattern to route calculations to provider-specific 
SDKs (OpenAI, Google, Anthropic) or local transformers, ensuring accuracy 
across different architectures. Includes a resilient heuristic fallback 
mechanism for offline or unsupported scenarios.
"""

import logging
from typing import Dict, Optional

from transcriptor4ai.core.processing.strategies.anthropic import AnthropicApiStrategy
from transcriptor4ai.core.processing.strategies.base import DEFAULT_MODEL, TokenizerStrategy
from transcriptor4ai.core.processing.strategies.google import GoogleApiStrategy
from transcriptor4ai.core.processing.strategies.heuristic import HeuristicStrategy
from transcriptor4ai.core.processing.strategies.local import MistralStrategy, TransformersStrategy
from transcriptor4ai.core.processing.strategies.openai import TIKTOKEN_AVAILABLE, TiktokenStrategy

logger = logging.getLogger(__name__)


# ==============================================================================
# SERVICE ORCHESTRATION (FACADE)
# ==============================================================================

class TokenizerService:
    """
    Centralized service for model-aware token estimation.

    Orchestrates the selection of the appropriate counting strategy
    based on the target model name and manages graceful fallbacks.
    """

    def __init__(self) -> None:
        """
        Initialize the service and register strategy mappings.

        The strategy map allows for O(1) routing by model prefix.
        """
        self.heuristic = HeuristicStrategy()

        # Mapping model prefixes to specialized strategies
        self._strategy_map: Dict[str, TokenizerStrategy] = {
            "gpt": TiktokenStrategy(),
            "o1": TiktokenStrategy(),
            "o3": TiktokenStrategy(),
            "o4": TiktokenStrategy(),
            "gemini": GoogleApiStrategy(),
            "claude": AnthropicApiStrategy(),
            "mistral": MistralStrategy(),
            "magistral": MistralStrategy(),
            "codestral": MistralStrategy(),
            "devstral": MistralStrategy(),
            "llama": TransformersStrategy(),
            "qwen": TransformersStrategy(),
            "qwq": TransformersStrategy(),
            "deepseek": TransformersStrategy(),
            "falcon": TransformersStrategy(),
        }

    def count(self, text: str, model: str) -> int:
        """
        Determine strategy and calculate token count.

        Handles special cases and provides robust error handling
        to prevent pipeline failures.

        Args:
            text: Raw input text to tokenize.
            model: Selected LLM identifier or architecture name.

        Returns:
            int: Estimated or precise token count.
        """
        if not text:
            return 0

        model_lower = model.lower()

        # 1. Special handling for default model selection
        if "- default model -" in model_lower:
            try:
                return TiktokenStrategy().count(text, "gpt-4o")
            except Exception as e:
                logger.warning(f"Default tokenizer execution failed: {e}. Routing to heuristic.")
                return self.heuristic.count(text, model)

        # 2. Iterate through mappings to find the specific provider strategy
        strategy: TokenizerStrategy = self.heuristic
        for prefix, strat in self._strategy_map.items():
            if prefix in model_lower:
                strategy = strat
                break

        # 3. Secondary architecture fallback
        if strategy == self.heuristic and TIKTOKEN_AVAILABLE:
            strategy = TiktokenStrategy()

        # 4. Execution with safe fallback
        try:
            return strategy.count(text, model)
        except Exception as e:
            logger.warning(
                f"Selected strategy {type(strategy).__name__} failed for model '{model}': {e}. "
                "Falling back to heuristic estimation."
            )
            return self.heuristic.count(text, model)


# ==============================================================================
# PUBLIC API
# ==============================================================================

# Singleton instance for global application access
_SERVICE_INSTANCE = TokenizerService()


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate the number of tokens for a given target model.

    Delegates the calculation to the global TokenizerService instance.

    Args:
        text: Input string content.
        model: Target model name (e.g., "GPT-4o", "Claude 3.5").

    Returns:
        int: Total token count.
    """
    return _SERVICE_INSTANCE.count(text, model)


def is_tiktoken_available() -> bool:
    """
    Check for local Tiktoken library availability.

    Returns:
        bool: True if tiktoken is successfully imported.
    """
    return TIKTOKEN_AVAILABLE