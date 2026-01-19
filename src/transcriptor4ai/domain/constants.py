from __future__ import annotations

"""
Domain Constants and Static Data Structures.

Provides centralized access to application-wide constants, including
supported AI model mappings, default file extension stacks, pricing metadata,
and system versioning.
"""

from typing import Any, Dict, List

CURRENT_CONFIG_VERSION = "2.1.0"
DEFAULT_OUTPUT_PREFIX = "transcription"
DEFAULT_MODEL_KEY = "- Default Model -"

# URL for live pricing synchronization
PRICING_DATA_URL = (
    "https://raw.githubusercontent.com/eparedes96/Transcriptor4AI/"
    "main/resources/pricing.json"
)

DEFAULT_STACKS: Dict[str, List[str]] = {
    "Python Data": [".py", ".ipynb", ".json", ".csv", ".yaml"],
    "Web Fullstack": [".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json"],
    "Java/Kotlin": [".java", ".kt", ".kts", ".xml", ".gradle", ".properties"],
    "C# / .NET": [".cs", ".csproj", ".sln", ".config"],
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
AI_MODELS: Dict[str, Dict[str, Any]] = {
    "- Default Model -": {
        "id": "gpt-4o",
        "provider": "- Default -",
        "input_cost_1k": 0.0025,
        "output_cost_1k": 0.010
    },

    "ChatGPT 5.2 (Preview)": {
        "id": "gpt-5.2-chat-latest",
        "provider": "OPENAI",
        "input_cost_1k": 0.010,
        "output_cost_1k": 0.030
    },
    "ChatGPT 4o": {
        "id": "chatgpt-4o-latest",
        "provider": "OPENAI",
        "input_cost_1k": 0.0025,
        "output_cost_1k": 0.010
    },
    "OpenAI o3": {
        "id": "o3",
        "provider": "OPENAI",
        "input_cost_1k": 0.015,
        "output_cost_1k": 0.060
    },

    "Claude 4.5 Sonnet": {
        "id": "claude-sonnet-4-5-20250929",
        "provider": "ANTHROPIC",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.015
    },
    "Claude 3.5 Sonnet": {
        "id": "claude-3-5-sonnet-20240620",
        "provider": "ANTHROPIC",
        "input_cost_1k": 0.003,
        "output_cost_1k": 0.015
    },

    "Gemini 2.5 Pro": {
        "id": "gemini-2.5-pro",
        "provider": "GOOGLE",
        "input_cost_1k": 0.00125,
        "output_cost_1k": 0.00375
    },
    "Gemini 2.5 Flash": {
        "id": "gemini-2.5-flash",
        "provider": "GOOGLE",
        "input_cost_1k": 0.0001,
        "output_cost_1k": 0.0003
    },

    "DeepSeek Chat V3.2": {
        "id": "deepseek-chat",
        "provider": "HF_LOCAL",
        "input_cost_1k": 0.00014,
        "output_cost_1k": 0.00028
    },
    "Qwen3 Instruct (235B)": {
        "id": "Qwen/Qwen3-235B-A22B-Instruct-2507",
        "provider": "HF_LOCAL",
        "input_cost_1k": 0.0003,
        "output_cost_1k": 0.0003
    }
}