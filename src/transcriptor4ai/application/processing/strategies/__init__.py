from __future__ import annotations

"""
Tokenization Strategies Facade.

Registers and exposes all available counting algorithms. 
Centralizes the detection of third-party tokenization libraries.
"""

# 1. EXPORT BASE: (Critical to fix "Cannot find reference")
from .base import DEFAULT_MODEL as DEFAULT_MODEL
from .base import TokenizerStrategy as TokenizerStrategy

# 2. EXPORT CONCRETE: (Expose specific implementations)
from .anthropic import ANTHROPIC_AVAILABLE as ANTHROPIC_AVAILABLE
from .anthropic import AnthropicApiStrategy as AnthropicApiStrategy

from .google import GOOGLE_AVAILABLE as GOOGLE_AVAILABLE
from .google import GoogleApiStrategy as GoogleApiStrategy

from .heuristic import HeuristicStrategy as HeuristicStrategy

from .local import MISTRAL_AVAILABLE as MISTRAL_AVAILABLE
from .local import TRANSFORMERS_AVAILABLE as TRANSFORMERS_AVAILABLE
from .local import MistralStrategy as MistralStrategy
from .local import TransformersStrategy as TransformersStrategy

from .openai import TIKTOKEN_AVAILABLE as TIKTOKEN_AVAILABLE
from .openai import TiktokenStrategy as TiktokenStrategy

# 3. DEFINE API: Define what is visible outside the package
__all__ = [
    "TokenizerStrategy",
    "DEFAULT_MODEL",
    "HeuristicStrategy",
    "TiktokenStrategy",
    "AnthropicApiStrategy",
    "GoogleApiStrategy",
    "TransformersStrategy",
    "MistralStrategy",
    "TIKTOKEN_AVAILABLE",
    "ANTHROPIC_AVAILABLE",
    "GOOGLE_AVAILABLE",
    "TRANSFORMERS_AVAILABLE",
    "MISTRAL_AVAILABLE",
]