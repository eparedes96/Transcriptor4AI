from __future__ import annotations

"""
OpenAI Tokenization Strategy.

Implements local BPE (Byte Pair Encoding) counting using the tiktoken library.
Supports modern o-series and GPT-4 architectures as well as legacy models.
This strategy is preferred for its high performance and offline capability.
"""

import logging
from typing import Final

from .base import TokenizerStrategy

# Standard logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# DYNAMIC DEPENDENCY CHECK
# ==============================================================================
TIKTOKEN_AVAILABLE: bool = False
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    pass

# ==============================================================================
# OPENAI TIKTOKEN STRATEGY
# ==============================================================================
class TiktokenStrategy(TokenizerStrategy):
    """
    OpenAI-specific encoder utilizing the tiktoken library for local counting.
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

        # 1. RESOLVE: Determine the correct encoding based on model family
        # Default to the most modern encoding (o-series/GPT-4o)
        encoding_name: Final[str] = "o200k_base"

        # Resolve legacy encoding for older GPT architectures
        if any(x in model_id.lower() for x in ["gpt-4-", "gpt-3.5", "legacy"]):
            encoding_name = "cl100k_base"

        try:
            # 2. LOAD: Retrieve encoding from tiktoken registry
            encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            logger.debug(f"Tiktoken: Encoding '{encoding_name}' not found, falling back.")
            encoding = tiktoken.get_encoding("cl100k_base")

        # 3. ENCODE: Calculate tokens without special character restrictions
        # disallowed_special=() allows strings that contain special tokens as raw text
        return len(encoding.encode(text, disallowed_special=()))