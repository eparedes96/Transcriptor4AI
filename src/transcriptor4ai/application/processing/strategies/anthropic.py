from __future__ import annotations

"""
Anthropic Claude Tokenization Strategy.

Utilizes the Anthropic SDK to perform remote token counting via 
the beta messages endpoint. Requires an active internet connection 
and a valid ANTHROPIC_API_KEY.
"""

import logging
import os

from .base import TokenizerStrategy

# Standard logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# DYNAMIC DEPENDENCY CHECK
# ==============================================================================
ANTHROPIC_AVAILABLE: bool = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

# ==============================================================================
# ANTHROPIC SDK STRATEGY
# ==============================================================================
class AnthropicApiStrategy(TokenizerStrategy):
    """
    Anthropic strategy utilizing the official SDK for Claude models.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Fetch token count from Claude remote counting service.

        Args:
            text: Input string.
            model_id: Logical model name to map to API identifiers.

        Returns:
            int: Input tokens returned by the API.
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("Library 'anthropic' is not installed.")

        # 1. VALIDATION: Ensure API access is configured
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY missing from environment variables.")

        try:
            # 2. MAPPING: Match logical model names to specific API tags
            client = anthropic.Anthropic(api_key=api_key)
            api_model: str = "claude-3-5-sonnet-20240620"

            if "4.5" in model_id:
                if "haiku" in model_id:
                    api_model = "claude-haiku-4-5-20251001"
                elif "opus" in model_id:
                    api_model = "claude-opus-4-5-20251101"
                else:
                    api_model = "claude-sonnet-4-5-20250929"
            elif "3.5" in model_id:
                api_model = "claude-3-5-sonnet-20240620"
            elif "3" in model_id and "opus" in model_id:
                api_model = "claude-3-opus-20240229"

            # 3. REQUEST: Execute token counting using the beta endpoint
            # Beta features are used here for token estimation accuracy.
            response = client.beta.messages.count_tokens(
                model=api_model,
                messages=[{"role": "user", "content": text}]
            )
            return int(response.input_tokens)

        except Exception as e:
            logger.error(f"Anthropic API strategy failed: {e}")
            raise