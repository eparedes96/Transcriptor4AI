from __future__ import annotations

"""
Token Counting Utility.

Provides precise token estimation for LLM contexts using a Hybrid Engine.
Implements a Strategy Pattern to route calculation to the appropriate provider:
- OpenAI: 'tiktoken' (Local/Fast).
- Google/Anthropic: Official SDKs (Network/Precise).
- Open Source (Llama/Mistral/DeepSeek): 'transformers'/'mistral_common' (Local/Cached).

Falls back to heuristic character density analysis on failure.
"""

import logging
import math
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Dependency Imports (Lazy/Safe)
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
# Constants & Fallbacks
# -----------------------------------------------------------------------------
CHARS_PER_TOKEN_AVG = 4
DEFAULT_MODEL = "- Default Model -"

# Global Cache for Transformers/Local Tokenizers to avoid reload latency
_TOKENIZER_CACHE: Dict[str, Any] = {}


# =============================================================================
# Strategy Interface
# =============================================================================
class TokenizerStrategy(ABC):
    """Abstract base class for counting strategies."""

    @abstractmethod
    def count(self, text: str, model_id: str) -> int:
        """
        Calculate tokens for the given text.
        Raises exception on failure to trigger fallback.
        """
        pass


# =============================================================================
# Concrete Strategies
# =============================================================================

class HeuristicStrategy(TokenizerStrategy):
    """Fallback strategy based on character density."""

    def count(self, text: str, model_id: str) -> int:
        return math.ceil(len(text) / CHARS_PER_TOKEN_AVG)


class TiktokenStrategy(TokenizerStrategy):
    """Strategy for OpenAI models using tiktoken."""

    def count(self, text: str, model_id: str) -> int:
        if not TIKTOKEN_AVAILABLE:
            raise ImportError("tiktoken not installed")

        encoding_name = "o200k_base"

        # Legacy mapping
        if any(x in model_id.lower() for x in ["gpt-4-", "gpt-3.5", "legacy"]):
            encoding_name = "cl100k_base"

        try:
            encoding = tiktoken.get_encoding(encoding_name)
        except ValueError:
            encoding = tiktoken.get_encoding("cl100k_base")

        return len(encoding.encode(text, disallowed_special=()))


class GoogleApiStrategy(TokenizerStrategy):
    """Strategy for Gemini models using Google GenAI SDK."""

    def count(self, text: str, model_id: str) -> int:
        if not GOOGLE_AVAILABLE:
            raise ImportError("google-generativeai not installed")

        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment")

        genai.configure(api_key=api_key)
        clean_model = model_id.lower().replace(" ", "-")
        if "gemini" not in clean_model:
            clean_model = "models/gemini-1.5-flash"
        elif not clean_model.startswith("models/"):
            clean_model = f"models/{clean_model}"

        model = genai.GenerativeModel(clean_model)
        response = model.count_tokens(text)
        return int(response.total_tokens)


class AnthropicApiStrategy(TokenizerStrategy):
    """Strategy for Claude models using Anthropic SDK."""

    def count(self, text: str, model_id: str) -> int:
        if not ANTHROPIC_AVAILABLE:
            raise ImportError("anthropic not installed")

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not found in environment")

        client = anthropic.Anthropic(api_key=api_key)

        # Mapping known display names to API IDs
        api_model = "claude-3-5-sonnet-20240620"
        if "3.5" in model_id:
            api_model = "claude-3-5-sonnet-20240620"
        elif "3" in model_id and "opus" in model_id:
            api_model = "claude-3-opus-20240229"

        response = client.beta.messages.count_tokens(
            model=api_model,
            messages=[{"role": "user", "content": text}]
        )
        return response.input_tokens


class TransformersStrategy(TokenizerStrategy):
    """Strategy for Open Source models (Llama, Qwen, DeepSeek)."""

    def count(self, text: str, model_id: str) -> int:
        if not TRANSFORMERS_AVAILABLE:
            raise ImportError("transformers not installed")

        # Map display names to HuggingFace Hub IDs
        hf_id = "meta-llama/Meta-Llama-3-8B"
        lower_id = model_id.lower()

        if "llama" in lower_id:
            hf_id = "meta-llama/Meta-Llama-3-8B"
        elif "qwen" in lower_id:
            hf_id = "Qwen/Qwen2.5-7B-Instruct"
        elif "deepseek" in lower_id:
            hf_id = "deepseek-ai/deepseek-coder-33b-instruct"

        # Cache mechanism
        if hf_id not in _TOKENIZER_CACHE:
            _TOKENIZER_CACHE[hf_id] = AutoTokenizer.from_pretrained(hf_id)

        tokenizer = _TOKENIZER_CACHE[hf_id]
        return len(tokenizer.encode(text))


class MistralStrategy(TokenizerStrategy):
    """Strategy for Mistral models using mistral_common."""

    def count(self, text: str, model_id: str) -> int:
        if not MISTRAL_AVAILABLE:
            raise ImportError("mistral_common not installed")

        if "mistral" not in _TOKENIZER_CACHE:
            _TOKENIZER_CACHE["mistral"] = MistralTokenizer.v3(is_tekken=True)

        tokenizer = _TOKENIZER_CACHE["mistral"]
        encoded = tokenizer.encode_chat_completion(
            ChatCompletionRequest(messages=[UserMessage(content=text)])
        )
        return len(encoded.tokens)


# =============================================================================
# Service Facade
# =============================================================================
class TokenizerService:
    """
    Factory service to route token counting requests.
    """

    def __init__(self) -> None:
        self.heuristic = HeuristicStrategy()

    def count(self, text: str, model: str) -> int:
        """
        Main entry point. Determines strategy based on model name.
        Handles errors gracefully by falling back to heuristic.
        """
        if not text:
            return 0

        if "- default model -" in model.lower():
            strategy = TiktokenStrategy()
            try:
                return strategy.count(text, "gpt-4o")
            except Exception as e:
                logger.warning(f"Default tokenizer failed: {e}. Using heuristic.")
                return self.heuristic.count(text, model)

        model_lower = model.lower()
        strategy: TokenizerStrategy

        # 1. Special Case: OCR / Vision
        if "ocr" in model_lower or "vision" in model_lower:
            logger.info("OCR model selected. Token counting skipped (Vision-based).")
            return 0

        # 2. Select Provider Strategy
        if "gpt" in model_lower or "o1" in model_lower or "o3" in model_lower:
            strategy = TiktokenStrategy()
        elif "gemini" in model_lower:
            strategy = GoogleApiStrategy()
        elif "claude" in model_lower:
            strategy = AnthropicApiStrategy()
        elif "mistral" in model_lower:
            strategy = MistralStrategy()
        elif any(x in model_lower for x in ["llama", "qwen", "deepseek", "falcon"]):
            strategy = TransformersStrategy()
        else:
            strategy = TiktokenStrategy() if TIKTOKEN_AVAILABLE else self.heuristic

        # 3. Execute with Safety Net
        try:
            return strategy.count(text, model)
        except Exception as e:
            logger.warning(f"Tokenizer strategy {type(strategy).__name__} failed: {e}. Using heuristic.")
            return self.heuristic.count(text, model)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
_SERVICE_INSTANCE = TokenizerService()


def count_tokens(text: str, model: str = DEFAULT_MODEL) -> int:
    """
    Estimate the number of tokens in a text string.
    Delegates to the Singleton TokenizerService.

    Args:
        text: The input text.
        model: The target model name (e.g., "Claude 3.5").

    Returns:
        int: The estimated token count.
    """
    return _SERVICE_INSTANCE.count(text, model)


def is_tiktoken_available() -> bool:
    """Legacy check for tiktoken availability."""
    return TIKTOKEN_AVAILABLE