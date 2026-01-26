from __future__ import annotations

"""
Google Gemini Tokenization Strategy.

Utilizes the Google GenAI SDK to perform remote token counting. 
Requires an active internet connection and a valid GOOGLE_API_KEY.
"""

import logging
import os

from .base import TokenizerStrategy

# Standard logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# DYNAMIC DEPENDENCY CHECK
# ==============================================================================
GOOGLE_AVAILABLE: bool = False
try:
    import google.genai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    pass

# ==============================================================================
# GOOGLE GENAI STRATEGY
# ==============================================================================
class GoogleApiStrategy(TokenizerStrategy):
    """
    Google Gemini strategy utilizing the official GenAI SDK for remote counting.
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

        # 1. VALIDATION: Check for credential availability in environment
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY missing from environment variables.")

        try:
            # 2. PREPARE: Initialize client and normalize model name
            client = genai.Client(api_key=api_key)
            clean_model = model_id.lower().replace(" ", "-")

            if "gemini" not in clean_model:
                clean_model = "gemini-1.5-flash"
            elif clean_model.startswith("models/"):
                clean_model = clean_model.replace("models/", "")

            # 3. REQUEST: Execute remote tokenization call
            response = client.models.count_tokens(
                model=clean_model,
                contents=text
            )
            return int(response.total_token_count)

        except Exception as e:
            logger.error(f"Google API strategy failed: {e}")
            raise