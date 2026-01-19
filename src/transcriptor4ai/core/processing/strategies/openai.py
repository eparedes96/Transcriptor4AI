from __future__ import annotations

"""
OpenAI Tokenization Strategy.

Implements local BPE (Byte Pair Encoding) counting using the tiktoken library.
Supports modern o-series and GPT-4 architectures as well as legacy models.
"""

import logging

from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

logger = logging.getLogger(__name__)

# --- Dynamic Dependency Check ---
TIKTOKEN_AVAILABLE = False
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    pass


class TiktokenStrategy(TokenizerStrategy):
    """
    OpenAI-specific encoder utilizing the tiktoken library.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Execute local BPE encoding via tiktoken.

        Args:
            text: Input string to tokenize.
            model_id: Model identifier to determine the encoding version.

        Returns:
            int: Calculated token count.
        """
        if not TIKTOKEN_AVAILABLE:
            raise ImportError("Library 'tiktoken' is not installed.")

        # Default to the most modern encoding (o-series/GPT-4o)
        encoding_name = "o200k_base"

        # Resolve legacy encoding for older GPT architectures
        if any(x in model_id.lower() for x in ["gpt-4-", "gpt-3.5", "legacy"]):
            encoding_name = "cl100k_base"

        try:
            encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            logger.debug(f"Encoding '{encoding_name}' not found, falling back to cl100k.")
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text, disallowed_special=()))