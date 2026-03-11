# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.1.0-orange.svg)]()
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![Architecture](https://img.shields.io/badge/architecture-Hexagonal-purple.svg)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is a professional Context Engineering Engine designed to transform complex local codebases into optimized, secure, and structured input for Large Language Models (LLMs) like **GPT-4o**, **Claude 3.5 Sonnet**, or **Gemini 1.5 Pro**.

Stop wasting time copying and pasting files or exposing sensitive data. Transcriptor4AI automates the creation of a "Master Context" that allows AI to understand your entire project architecture at once, with maximum token efficiency.

---

## 🌟 Why Transcriptor4AI v2.2.0?

Working with AI on enterprise projects presents critical challenges: **Context Limits**, **Security Risks**, **Execution Time**, and **Hidden API Costs**. The V2.2.0 release solves them through a strictly decoupled Hexagonal Architecture:

*   **Intelligent Caching**: Process 10,000+ files in seconds. The SQLite-backed engine skips unchanged files using a composite deterministic hash.
*   **Smart Economy**: Real-time financial awareness. It downloads live pricing metadata from LiteLLM and calculates exact prompt costs in USD before you send anything to the AI.
*   **Skeleton Mode**: Drastically reduce token usage by up to 70%. It uses Python's AST to strip function bodies while perfectly preserving class structures, signatures, and docstrings.
*   **Privacy First**: Local-only sanitization of API keys and OS paths. Your secrets never leave your machine.

---

## 🚀 Key Features

### 🛡️ Security & Privacy
*   **Secret Redaction**: Automatically identifies and masks high-entropy API keys (AWS, OpenAI) and generic credential assignments.
*   **Path Anonymization**: Replaces local system paths (e.g., `C:/Users/Admin`) with generic tags (`<USER_HOME>`) to protect developer identity.
*   **Gitignore Compliance**: Respects `.gitignore` rules natively to prevent leaking cache, builds, or `node_modules`.

### 📉 Smart Optimization
*   **Skeleton Mode (AST)**: Transforms complex logic into architectural skeletons (`def func(args): pass`), providing the AI with the map without the heavy implementation details.
*   **Code Minification**: Strips comments and excessive whitespace, reducing token footprint while preserving logical validity.
*   **Universal Token Proxy**: Uses local BPE encoding (`tiktoken`) for high-fidelity token estimation without requiring remote API keys.

### ⚡ Performance & Finance
*   **SQLite Cache Engine**: Cross-session persistence. Re-running a transcription after changing one file only processes that specific file.
*   **Live Cost Estimator**: Predicts the exact cost of your context window based on dynamic remote pricing tables.

### ⚙️ Professional Workflow
*   **Modern GUI**: A responsive, thread-safe interface (CustomTkinter) with Dashboard, Advanced Settings, and real-time System Logs.
*   **Silent OTA Updates**: Background lifecycle management downloads and verifies binary integrity (SHA-256) without blocking your workflow.
*   **Profile Management**: Save different configurations (e.g., "Full Audit" vs "Skeleton Map") and switch instantly.

---

## 📦 Installation

### Prerequisites
*   Python 3.12 or higher.
*   Conda (Recommended for clean environments).

### Setup
```bash
# Clone and enter the repository
git clone https://github.com/eparedes96/Transcriptor4AI.git
cd Transcriptor4AI

# Install dependencies via Conda (Production environment)
conda env update --file environment.yml --prune
conda activate transcriptor4ai

# Install the package in editable mode
pip install -e .
```

---

## 🖥️ Usage

### 1. Graphical User Interface (GUI)
The completely redesigned, non-blocking interface offering a comprehensive dashboard experience.

```bash
# Using the installed entry point
transcriptor-gui

# OR running directly from source
python src/transcriptor4ai/interface/gui/gui_launcher.py
```

*   **Simulation Mode**: Use **"SIMULATE"** to perform a dry-run. It uses the cache, calculates exact tokens, and estimates financial cost without writing final files to disk.

### 2. Command Line Interface (CLI)
Built for CI/CD pipelines, headless environments, and power users.

**High-Security Skeleton Extraction:**
```bash
transcriptor-cli -i ./src -o ./out --unified-only --skeleton --sanitize --tree --classes --functions
```

**JSON Output for Automation:**
```bash
transcriptor-cli -i ./my_app --dry-run --json
```

---

## 📂 Output Artifacts

Every successful run generates a structured directory (default: `transcript/`) containing:

1.  **`full_context.txt`**: The unified AI-ready document aggregating the Tree, Modules, Tests, and Resources.
2.  **`tree.txt`**: A visual ASCII map of your project structure, enhanced with AST symbols.
3.  **`modules.txt / tests.txt`**: Categorized logic separated for fine-grained manual control.
4.  **`errors.txt`**: A transparent diagnostic log of any system-level read errors (e.g., locked files).

---

## ⚙️ Configuration

Transcriptor4AI stores preferences and persistent state in `config.json` inside your OS user data folder (`%LOCALAPPDATA%` or `~/.transcriptor4ai`).

**Sample V2.2.0 Configuration:**
```json
{
    "version": "2.2.0",
    "app_settings": {
        "theme": "System",
        "auto_check_updates": true
    },
    "last_session": {
        "target_model": "Claude 3.5 Sonnet",
        "processing_depth": "skeleton",
        "enable_sanitizer": true,
        "minify_output": true,
        "respect_gitignore": true
    }
}
```

---

## 🛠️ Development & Architecture

This project is strictly governed by a **Hexagonal Architecture (Ports and Adapters)** pattern. 
*   **Domain**: Pure business rules, Data Models (`PipelineResult`), and Interface Ports.
*   **Application**: Use cases, Pipeline Orchestrator, Transformation Services, and Caching logic.
*   **Infrastructure**: Concrete adapters for SQLite, GitHub APIs, and OS FileSystem.
*   **Interface**: CLI args parser and CustomTkinter Controllers/Views wired via Dependency Injection.

### Quality Assurance (Quality Gate)
Run the comprehensive industrial test suite (Unit, Integration, E2E) mapped against the architecture:
```bash
# Run the automated CI Quality Gate (Checks Ruff, Mypy, and Pytest)
python scripts/ci_quality_gate.py

# Or run tests manually with detailed verbosity
pytest -v -ra --showlocals
```

### Standalone Build
To generate an independent executable (`.exe`) embedding the dynamic model pricing snapshot:
```bash
# The build script automatically downloads the latest model pricing 
# before packaging the executable via PyInstaller.
python scripts/build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com