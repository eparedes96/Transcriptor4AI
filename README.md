# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-2.0.0-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is a professional Context Engineering Engine designed to transform complex local codebases into optimized, secure, and structured input for Large Language Models (LLMs) like **GPT-4o**, **Claude 3.5**, or **Gemini 1.5**.

Stop wasting time copying and pasting files or exposing sensitive data. Transcriptor4AI automates the creation of a "Master Context" that allows AI to understand your entire project architecture at once.

---

## 🌟 Why Transcriptor4AI v2.0?

Working with AI on large projects presents three challenges: **Context Limits**, **Security Risks**, and **Tooling Friction**. The new v2.0 release solves them with enterprise-grade architecture:

*   **Privacy First**: Local-only sanitization of API keys and paths. Your secrets never leave your machine.
*   **Hybrid Precision**: New **Strategy-based Tokenizer** that uses the exact counting method for your target model (Tiktoken for OpenAI, Google SDK for Gemini, Anthropic SDK for Claude).
*   **Modern Experience**: A completely rewritten **GUI (CustomTkinter)** with Dark Mode, intuitive dashboards, and silent background updates.
*   **Structural Clarity**: Generates a deep AST map of your project, allowing the AI to "see" class hierarchies and function signatures.

---

## 🚀 Key Features

### 🛡️ Security & Privacy
*   **Secret Redaction**: Automatically identifies and masks API keys (AWS, OpenAI, Google), passwords, and tokens.
*   **Path Anonymization**: Replaces local system paths (e.g., `C:/Users/Admin`) with generic tags (`<USER_HOME>`) to protect identity.
*   **Gitignore Compliance**: Respects `.gitignore` rules natively to prevent leaking temporary files or `node_modules`.

### 📉 Smart Optimization
*   **Code Minification**: Strips comments and excessive whitespace, reducing token usage by ~25% while preserving logic.
*   **Hybrid Tokenizer**: No more guessing. The engine selects the correct tokenizer strategy (OpenAI, Anthropic, Google, or Llama/Mistral) based on your selected model.

### 🌳 Structural Intelligence
*   **Static Analysis**: Generates a project tree that details **Classes, Functions, and Methods** using Python's AST without executing code.
*   **Contextual Separation**: Automatically categorizes files into Modules (Logic), Tests, and Resources (Config/Docs).

### ⚙️ Professional Workflow
*   **Modern GUI**: A responsive, thread-safe interface with Dashboard, Settings, and Logs tabs.
*   **Silent OTA**: Background updates download and verify integrity (SHA-256) while you work, applying only when you restart.
*   **Profiles**: Save different configurations (e.g., "Full Audit" vs "Minimal Logic") and switch instantly.

---

## 📦 Installation

### Prerequisites
*   Python 3.12 or higher.
*   Conda (Recommended).

### Setup
```bash
# Clone and enter the repo
git clone https://github.com/eparedes96/Transcriptor4AI.git
cd Transcriptor4AI

# Install dependencies via Conda (Production environment)
conda env update --file environment.yml --prune
conda activate transcriptor4ai

# Install package in editable mode
pip install -e .
```

---

## 🖥️ Usage

### 1. Graphical User Interface (GUI)
The completely redesigned interface offering a dashboard experience.

```bash
# Using the installed command
transcriptor-gui

# OR running from source
python src/transcriptor4ai/interface/gui/app.py
```

*   **Simulation Mode**: Use **"SIMULATE"** to perform a dry-run. It calculates tokens and shows the file structure without writing to disk.

### 2. Command Line Interface (CLI)
For CI/CD pipelines and power users.

**Basic Context Extraction:**
```bash
transcriptor-cli -i ./my_app -o ./out --tree
```

**High-Security & Optimized Context:**
```bash
transcriptor-cli -i ./src -o ./out --unified-only --minify --sanitize --tree --classes --functions
```

---

## 📂 Output Artifacts

Every run generates a structured directory (default: `transcript/`) with:

1.  **`full_context.txt`**: The unified AI-ready document containing Tree, Modules, Tests, and Resources.
2.  **`tree.txt`**: A visual map of your project structure with AST symbols.
3.  **`modules.txt / tests.txt`**: Separated logic for fine-grained manual control.
4.  **`errors.txt`**: A transparent log of any read errors (e.g., permission issues).

---

## ⚙️ Configuration

Transcriptor4AI stores preferences in `config.json` inside your user data folder. Version 2.0.0 introduces a hierarchical structure.

**Sample Configuration:**
```json
{
    "version": "2.0.0",
    "app_settings": {
        "theme": "SystemDefault",
        "auto_check_updates": true
    },
    "last_session": {
        "target_model": "Claude 3.5 Sonnet",
        "enable_sanitizer": true,
        "minify_output": true,
        "respect_gitignore": true
    }
}
```

---

## 🛠️ Development & Architecture

This project follows a **Hexagonal Architecture** with a strict **MVC** pattern for the GUI:
*   **Domain**: Data models and business rules.
*   **Core**: Pipeline logic, AST analysis, and Processing strategies.
*   **Infra**: FileSystem, Thread-safe Logging, and Network adapters.
*   **Interface**: CustomTkinter controllers and views.

### Quality Assurance
Run the comprehensive test suite (Unit, Integration, E2E):
```bash
# Run the complete industrial test suite
pytest -v

# Static type analysis with strict checking
mypy src/transcriptor4ai

# Linting and formatting check
ruff check .
```

### Standalone Build
To create a standalone executable (`.exe`):
```bash
# Use the automated build script
python scripts/build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com