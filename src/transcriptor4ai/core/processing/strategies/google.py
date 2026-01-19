from __future__ import annotations

"""
Google Gemini Tokenization Strategy.

Utilizes the Google GenAI SDK to perform remote token counting. 
Requires an active internet connection and a valid GOOGLE_API_KEY.
"""

import logging
import os

from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

logger = logging.getLogger(__name__)

# --- Dynamic Dependency Check ---
GOOGLE_AVAILABLE = False
try:
    import google.genai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    pass


class GoogleApiStrategy(TokenizerStrategy):
    """
    Google Gemini strategy utilizing the official GenAI SDK.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Fetch token count from Gemini remote service via GenAI Client.

        Args:
            text: Input string.
            model_id: Target Gemini model identifier.

        Returns:
            int: Token count returned by the API.
        """
        if not GOOGLE_AVAILABLE:
            raise ImportError("Library 'google-genai' is not installed.")

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY missing from environment variables.")

        try:
            client = genai.Client(api_key=api_key)
            clean_model = model_id.lower().replace(" ", "-")

            # Default to flash if model resolution is ambiguous
            if "gemini" not in clean_model:
                clean_model = "gemini-1.5-flash"
            elif clean_model.startswith("models/"):
                clean_model = clean_model.replace("models/", "")

            response = client.models.count_tokens(
                model=clean_model,
                contents=text
            )
            return int(response.total_token_count)
        except Exception as e:
            logger.error(f"Google API tokenization failed: {e}")
            raise