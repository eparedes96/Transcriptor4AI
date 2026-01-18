from __future__ import annotations

"""
Local SDK Tokenization Strategies.

Leverages locally installed libraries (transformers, mistral_common) to 
perform high-fidelity tokenization for open-source models without 
requiring external network access.
"""

import logging
from typing import Any, Dict

from transcriptor4ai.core.processing.strategies.base import TokenizerStrategy

logger = logging.getLogger(__name__)

# --- Dynamic Dependency Check ---
TRANSFORMERS_AVAILABLE = False
try:
    from transformers import AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

MISTRAL_AVAILABLE = False
try:
    from mistral_common.protocol.instruct.messages import UserMessage
    from mistral_common.protocol.instruct.request import ChatCompletionRequest
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
    MISTRAL_AVAILABLE = True
except ImportError:
    pass

# Global cache to prevent redundant I/O when loading heavy tokenizer files
_TOKENIZER_CACHE: Dict[str, Any] = {}


class TransformersStrategy(TokenizerStrategy):
    """
    Open-source model strategy using HuggingFace AutoTokenizers.
    Supports Llama, Qwen, and DeepSeek families.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Execute local tokenization via transformers SDK.

        Args:
            text: Input string.
            model_id: Model name to resolve the correct HF repository.

        Returns:
            int: Calculated token count.
        """
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("Package 'transformers' is not installed.")

        # Map display names to HuggingFace Hub repositories
        hf_id = "meta-llama/Meta-Llama-3-8B"
        lower_id = model_id.lower()

        if "llama" in lower_id:
            hf_id = "meta-llama/Meta-Llama-3-8B"
        elif "qwen" in lower_id or "qwq" in lower_id:
            hf_id = "Qwen/Qwen2.5-7B-Instruct"
        elif "deepseek" in lower_id:
            hf_id = "deepseek-ai/deepseek-coder-33b-instruct"

        try:
            # Persist tokenizer in cache to avoid reload overhead
            if hf_id not in _TOKENIZER_CACHE:
                logger.debug(f"Loading local tokenizer for {hf_id}...")
                _TOKENIZER_CACHE[hf_id] = AutoTokenizer.from_pretrained(hf_id)

            tokenizer = _TOKENIZER_CACHE[hf_id]
            return int(len(tokenizer.encode(text)))
        except Exception as e:
            logger.error(f"Transformers tokenization failed for {hf_id}: {e}")
            raise


class MistralStrategy(TokenizerStrategy):
    """
    Mistral-specific strategy using the mistral_common library.
    Ensures high-fidelity counting for Mistral and Codestral models.
    """

    def count(self, text: str, model_id: str) -> int:
        """
        Execute tokenization using Mistral's reference encoder.

        Args:
            text: Input string.
            model_id: Specific Mistral model identifier.

        Returns:
            int: Calculated token count.
        """
        if not MISTRAL_AVAILABLE:
            raise ImportError("Package 'mistral_common' is not installed.")

        try:
            if "mistral" not in _TOKENIZER_CACHE:
                _TOKENIZER_CACHE["mistral"] = MistralTokenizer.v3(is_tekken=True)

            tokenizer = _TOKENIZER_CACHE["mistral"]
            encoded = tokenizer.encode_chat_completion(
                ChatCompletionRequest(messages=[UserMessage(content=text)])
            )
            return int(len(encoded.tokens))
        except Exception as e:
            logger.error(f"Mistral tokenization failed: {e}")
            raise