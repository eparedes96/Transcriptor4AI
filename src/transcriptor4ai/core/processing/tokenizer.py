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
import math
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type, cast

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# DEPENDENCY MANAGEMENT (LAZY LOADING)
# -----------------------------------------------------------------------------

TIKTOKEN_AVAILABLE = False
try:
    import tiktoken

    TIKTOKEN_AVAILABLE = True
except ImportError:
    pass

GOOGLE_AVAILABLE = False
try:
    import google.generativeai as genai

    GOOGLE_AVAILABLE = True
except ImportError:
    pass

ANTHROPIC_AVAILABLE = False
try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    pass

TRANSFORMERS_AVAILABLE = False
try:
    from transformers import AutoTokenizer

    TRANSFORMERS_AVAILABLE = True
except ImportError:
    pass

MISTRAL_AVAILABLE = False
try:
    from mistral_common.tokens.tokenizers.mistral import MistralTokenizer
    from mistral_common.protocol.instruct.messages import UserMessage
    from mistral_common.protocol.instruct.request import ChatCompletionRequest

    MISTRAL_AVAILABLE = True
except ImportError:
    pass

# -----------------------------------------------------------------------------
# GLOBAL CONSTANTS & CACHE
# -----------------------------------------------------------------------------

CHARS_PER_TOKEN_AVG = 4
DEFAULT_MODEL = "- Default Model -"

# Global Cache to prevent redundant I/O when loading local tokenizers (HF/Mistral)
_TOKENIZER_CACHE: Dict[str, Any] = {}


# -----------------------------------------------------------------------------
# STRATEGY INTERFACES
# -----------------------------------------------------------------------------

class TokenizerStrategy(ABC):
    """
    Abstract base class for model-specific tokenization algorithms.
    """

    @abstractmethod
    def count(self, text: str, model_id: str) -> int:
        """
        Calculate the token count for a given text segment.

        Args:
            text: Input string to be tokenized.
            model_id: Specific model identifier for encoding selection.

        Returns:
            int: Total token count.
        """
        pass


# -----------------------------------------------------------------------------
# CONCRETE STRATEGIES: LOCAL ENCODERS
# -----------------------------------------------------------------------------

class HeuristicStrategy(TokenizerStrategy):
    """
    Fallback algorithm using character density estimation.
    Used when specific libraries or network access are unavailable.
    """

    def count(self, text: str, model_id: str) -> int:
        """Estimate tokens using the global characters-to-token ratio."""
        return math.ceil(len(text) / CHARS_PER_TOKEN_AVG)


class TiktokenStrategy(TokenizerStrategy):
    """
    OpenAI-specific encoder using the tiktoken library.
    Optimized for GPT-3.5, GPT-4, and the O-series models.
    """

    def count(self, text: str, model_id: str) -> int:
        """Execute local BPE encoding via tiktoken."""
        if not TIKTOKEN_AVAILABLE:
            raise ImportError("tiktoken not installed")

        encoding_name = "o200k_base"

        # Resolve legacy encoding for older GPT architectures
        if any(x in model_id.lower() for x in ["gpt-4-", "gpt-3.5", "legacy"]):
            encoding_name = "cl100k_base"

        try:
            encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text, disallowed_special=()))


# -----------------------------------------------------------------------------
# CONCRETE STRATEGIES: REMOTE SDKS
# -----------------------------------------------------------------------------

class GoogleApiStrategy(TokenizerStrategy):
    """
    Google Gemini strategy utilizing the Generative AI SDK.
    Requires active network and valid GOOGLE_API_KEY.
    """

    def count(self, text: str, model_id: str) -> int:
        """Fetch token count from Gemini remote service."""
        if not GOOGLE_AVAILABLE:
            raise ImportError("google-generativeai not installed")

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        clean_model = model_id.lower().replace(" ", "-")

        # Default to flash if model resolution is ambiguous
        if "gemini" not in clean_model:
            clean_model = "models/gemini-1.5-flash"
        elif not clean_model.startswith("models/"):
            clean_model = f"models/{clean_model}"

        model = genai.GenerativeModel(clean_model)
        response = model.count_tokens(text)
        return int(response.total_tokens)


class AnthropicApiStrategy(TokenizerStrategy):
    """
    Anthropic strategy utilizing the official SDK for Claude models.
    Requires active network and ANTHROPIC_API_KEY.
    """

    def count(self, text: str, model_id: str) -> int:
        """Fetch token count from Claude beta counting service."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic not installed")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

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


# -----------------------------------------------------------------------------
# CONCRETE STRATEGIES: OPEN SOURCE / HF
# -----------------------------------------------------------------------------

class TransformersStrategy(TokenizerStrategy):
    """
    Open-source model strategy using HuggingFace AutoTokenizers.
    Supports Llama, Qwen, and DeepSeek families.
    """

    def count(self, text: str, model_id: str) -> int:
        """Execute local tokenization via transformers SDK."""
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not installed")

        # Map display names to HuggingFace Hub repositories
        hf_id = "meta-llama/Meta-Llama-3-8B"
        lower_id = model_id.lower()

        if "llama" in lower_id:
            hf_id = "meta-llama/Meta-Llama-3-8B"
        elif "qwen" in lower_id or "qwq" in lower_id:
            hf_id = "Qwen/Qwen2.5-7B-Instruct"
        elif "deepseek" in lower_id:
            hf_id = "deepseek-ai/deepseek-coder-33b-instruct"

        # Persist tokenizer in cache to avoid reload overhead
        if hf_id not in _TOKENIZER_CACHE:
            _TOKENIZER_CACHE[hf_id] = AutoTokenizer.from_pretrained(hf_id)

        tokenizer = _TOKENIZER_CACHE[hf_id]
        return int(len(tokenizer.encode(text)))


class MistralStrategy(TokenizerStrategy):
    """
    Mistral-specific strategy using the mistral_common library.
    Ensures high-fidelity counting for Mistral and Codestral models.
    """

    def count(self, text: str, model_id: str) -> int:
        """Execute tokenization using Mistral's reference encoder."""
        if not MISTRAL_AVAILABLE:
            raise ImportError("mistral_common not installed")

        if "mistral" not in _TOKENIZER_CACHE:
            _TOKENIZER_CACHE["mistral"] = MistralTokenizer.v3(is_tekken=True)

        tokenizer = _TOKENIZER_CACHE["mistral"]
        encoded = tokenizer.encode_chat_completion(
            ChatCompletionRequest(messages=[UserMessage(content=text)])
        )
        return int(len(encoded.tokens))


# -----------------------------------------------------------------------------
# SERVICE ORCHESTRATION (FACADE)
# -----------------------------------------------------------------------------

class TokenizerService:
    """
    Centralized service for model-aware token estimation.

    Orchestrates the selection of the appropriate counting strategy
    based on the target model name and manages graceful fallbacks.
    """

    def __init__(self) -> None:
        """Initialize the service and register strategy mappings."""
        self.heuristic = HeuristicStrategy()

        # Mapping model prefixes to specialized strategies for O(1) routing
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

        Handles special cases such as OCR/Vision models and provides
        robust error handling to prevent pipeline failures.

        Args:
            text: Raw input text.
            model: Selected LLM identifier.

        Returns:
            int: Estimated or precise token count.
        """
        if not text:
            return 0

        model_lower = model.lower()

        # Skip counting for Vision-based models where text context is not applicable
        if "ocr" in model_lower or "vision" in model_lower:
            logger.info("Vision model detected. Skipping token counting.")
            return 0

        # Special handling for default model selection
        if "- default model -" in model_lower:
            try:
                return TiktokenStrategy().count(text, "gpt-4o")
            except Exception as e:
                logger.warning(f"Default tokenizer execution failed: {e}. Routing to heuristic.")
                return self.heuristic.count(text, model)

        # Iterate through mappings to find the specific provider strategy
        strategy: TokenizerStrategy = self.heuristic
        for prefix, strat in self._strategy_map.items():
            if prefix in model_lower:
                strategy = strat
                break

        # Secondary fallback if no direct prefix match found for known architectures
        if strategy == self.heuristic and TIKTOKEN_AVAILABLE:
            strategy = TiktokenStrategy()

        try:
            return strategy.count(text, model)
        except Exception as e:
            # Final safety net to ensure a result is returned
            logger.warning(f"Selected strategy {type(strategy).__name__} failed: {e}. Using heuristic fallback.")
            return self.heuristic.count(text, model)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

# Singleton instance for global application access
_SERVICE_INSTANCE = TokenizerService()


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate the number of tokens for the target model.

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