from __future__ import annotations

"""
Domain Constants and Static Data Structures.

Provides centralized access to application-wide constants, including
discovery metadata, default file extension stacks, and system versioning.
"""

from typing import Dict, List

# -----------------------------------------------------------------------------
# VERSIONING AND METADATA
# -----------------------------------------------------------------------------
CURRENT_CONFIG_VERSION = "2.1.0"
DEFAULT_OUTPUT_PREFIX = "transcription"
DEFAULT_MODEL_KEY = "- Default Model -"

# -----------------------------------------------------------------------------
# DYNAMIC MODEL DISCOVERY (LiteLLM Authority)
# -----------------------------------------------------------------------------
# Master repository for live pricing and context window synchronization
MODEL_DATA_URL = (
    "https://raw.githubusercontent.com/BerriAI/litellm/main/"
    "model_prices_and_context_window.json"
)

# Relative asset path for the build-time snapshot (Offline-First strategy)
BUNDLED_DATA_FILENAME = "bundled_models.json"

# Local cache filename for persistent pricing storage across sessions
LOCAL_PRICING_FILENAME = "pricing_cache.json"

# -----------------------------------------------------------------------------
# FILE STACKS AND EXTENSIONS
# -----------------------------------------------------------------------------
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