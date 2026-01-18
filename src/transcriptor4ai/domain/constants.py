from __future__ import annotations

"""
Domain Constants and Static Data Structures.

Provides centralized access to application-wide constants, including 
supported AI model mappings, default file extension stacks, and 
system versioning.
"""

from typing import Dict, List

# -----------------------------------------------------------------------------
# SYSTEM VERSIONING
# -----------------------------------------------------------------------------

CURRENT_CONFIG_VERSION = "2.0.1"
DEFAULT_OUTPUT_PREFIX = "transcription"
DEFAULT_MODEL_KEY = "- Default Model -"

# -----------------------------------------------------------------------------
# STACK PRESETS
# -----------------------------------------------------------------------------

DEFAULT_STACKS: Dict[str, List[str]] = {
    "Python Data": [".py", ".ipynb", ".json", ".csv", ".yaml"],
    "Web Fullstack": [".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"],
    "Java/Kotlin": [".java", ".kt", ".kts", ".xml", ".gradle", ".properties"],
    "C# / .NET": [".cs", ".csproj", ".sln", ".xml", ".config", ".json"],
    "C / C++": [".c", ".cpp", ".h", ".hpp", "CMakeLists.txt", "Makefile"],
    "Mobile (Swift/Dart)": [".swift", ".dart", ".yaml", ".xml", ".plist"],
    "Rust": [".rs", ".toml"],
    "Go": [".go", ".mod", ".sum"],
    "PHP Legacy": [".php", ".phtml", "composer.json", ".ini"],
    "Shell / Ops": [
        ".sh", ".bash", ".zsh", ".ps1", ".bat",
        "Dockerfile", ".dockerignore", ".yaml", ".yml"
    ],
    "Documentation": [".md", ".rst", ".txt", ".pdf"],
}

# -----------------------------------------------------------------------------
# AI PROVIDER REGISTRY
# -----------------------------------------------------------------------------

AI_MODELS: Dict[str, Dict[str, str]] = {
    "- Default Model -": {"id": "gpt-4o", "provider": "- Default -"},

    # OpenAI Family
    "ChatGPT 5.2 (Preview)": {"id": "gpt-5.2-chat-latest", "provider": "OPENAI"},
    "ChatGPT 4o": {"id": "chatgpt-4o-latest", "provider": "OPENAI"},
    "GPT-5.2 (API)": {"id": "gpt-5.2", "provider": "OPENAI"},
    "GPT-5.2 Codex": {"id": "gpt-5.2-codex", "provider": "OPENAI"},
    "OpenAI o3": {"id": "o3", "provider": "OPENAI"},
    "OpenAI o4-mini": {"id": "o4-mini", "provider": "OPENAI"},
    "OpenAI o3 Deep Research": {"id": "o3-deep-research", "provider": "OPENAI"},
    "OpenAI o4-mini Deep Research": {"id": "o4-mini-deep-research", "provider": "OPENAI"},

    # Anthropic Family
    "Claude 4.5 Sonnet": {"id": "claude-sonnet-4-5-20250929", "provider": "ANTHROPIC"},
    "Claude 4.5 Haiku": {"id": "claude-haiku-4-5-20251001", "provider": "ANTHROPIC"},
    "Claude 4.5 Opus": {"id": "claude-opus-4-5-20251101", "provider": "ANTHROPIC"},
    "Claude 3.5 Sonnet": {"id": "claude-3-5-sonnet-20240620", "provider": "ANTHROPIC"},

    # Google Family
    "Gemini 3 Pro (Preview)": {"id": "gemini-3-pro-preview", "provider": "GOOGLE"},
    "Gemini 3 Flash (Preview)": {"id": "gemini-3-flash-preview", "provider": "GOOGLE"},
    "Gemini 2.5 Pro": {"id": "gemini-2.5-pro", "provider": "GOOGLE"},
    "Gemini 2.5 Flash": {"id": "gemini-2.5-flash", "provider": "GOOGLE"},
    "Gemini 2.5 Flash-Lite": {"id": "gemini-2.5-flash-lite", "provider": "GOOGLE"},

    # Mistral Family
    "Mistral Large 3 (2512)": {"id": "mistral-large-2512", "provider": "MISTRAL"},
    "Mistral Medium 3.1 (2508)": {"id": "mistral-medium-2508", "provider": "MISTRAL"},
    "Mistral Small 3.2 (2506)": {"id": "mistral-small-2506", "provider": "MISTRAL"},
    "Magistral Medium (Reasoning)": {"id": "magistral-medium-2509", "provider": "MISTRAL"},
    "Magistral Small (Reasoning)": {"id": "magistral-small-2509", "provider": "MISTRAL"},
    "Codestral (2508)": {"id": "codestral-2508", "provider": "MISTRAL"},
    "Devstral (Agents)": {"id": "devstral-2512", "provider": "MISTRAL"},
    "Devstral Medium": {"id": "devstral-medium-2507", "provider": "MISTRAL"},
    "Devstral Small": {"id": "devstral-small-2507", "provider": "MISTRAL"},
    "Devstral Small (Labs)": {"id": "labs-devstral-small-2512", "provider": "MISTRAL"},

    # DeepSeek & Local HF Architectures
    "DeepSeek Chat V3.2": {"id": "deepseek-chat", "provider": "HF_LOCAL"},
    "DeepSeek Reasoner (Thinking)": {"id": "deepseek-reasoner", "provider": "HF_LOCAL"},
    "Qwen3 Instruct (235B)": {"id": "Qwen/Qwen3-235B-A22B-Instruct-2507", "provider": "HF_LOCAL"},
    "Qwen3 Thinking (235B)": {"id": "Qwen/Qwen3-235B-A22B-Thinking-2507", "provider": "HF_LOCAL"},
    "Qwen3-Next Instruct (80B)": {"id": "Qwen/Qwen3-Next-80B-A3B-Instruct", "provider": "HF_LOCAL"},
    "Qwen3-Next Thinking (80B)": {"id": "Qwen/Qwen3-Next-80B-A3B-Thinking", "provider": "HF_LOCAL"},
    "QwQ-32b (Legacy Reasoning)": {"id": "qwq-32b", "provider": "HF_LOCAL"},
    "Qwen3 Coder (480B)": {"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct", "provider": "HF_LOCAL"},
    "Qwen3 Coder Small (30B)": {"id": "qwen3-coder-30b-a3b-instruct", "provider": "HF_LOCAL"},
    "Qwen2.5 Coder (32B)": {"id": "Qwen/Qwen2.5-Coder-32B-Instruct", "provider": "HF_LOCAL"},
    "Llama 3 70B": {"id": "meta-llama/Meta-Llama-3-70B", "provider": "HF_LOCAL"},
}