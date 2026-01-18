from __future__ import annotations

"""
Anthropic Claude Tokenization Strategy.

Utilizes the Anthropic SDK to perform remote token counting via 
the beta messages endpoint. Requires an active internet connection 
and a valid ANTHROPIC_API_KEY.
"""

import os
import logging
from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

logger = logging.getLogger(__name__)

# --- Dynamic Dependency Check ---
ANTHROPIC_AVAILABLE = False
try:
    import anthropic
    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass


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

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY missing from environment variables.")

        try:
            client = anthropic.Anthropic(api_key=api_key)

            # Mapping logical model names to API identifiers
            api_model = "claude-3-5-sonnet-20240620"

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

            response = client.beta.messages.count_tokens(
                model=api_model,
                messages=[{"role": "user", "content": text}]
            )
            return int(response.input_tokens)
        except Exception as e:
            logger.error(f"Anthropic API tokenization failed: {e}")
            raise