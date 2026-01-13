# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.6.0-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is a professional engine designed to transform complex local codebases into optimized, secure, and structured context for Large Language Models (LLMs) like **GPT-4o**, **Claude 3.5**, or **Gemini**.

Stop wasting time copying and pasting files or exposing sensitive data. Transcriptor4AI automates the creation of a "Master Context" that allows AI to understand your entire project architecture at once.

---

## 🌟 Why Transcriptor4AI?

When working with AI and large projects, you face three main challenges: **Context Limits**, **Security Risks**, and **Manual Toil**. Transcriptor4AI solves them all:

*   **Privacy First**: Never send an API key or a local path to the cloud by mistake. The sanitizer runs locally.
*   **Token Efficiency**: Reduce the cost of your prompts by stripping away redundant code and comments (Minification).
*   **Structural Clarity**: Provide the AI with a map of your project (AST Tree) so it understands how classes and functions relate.
*   **Industrial Performance**: Built with a parallel streaming engine to handle everything from small scripts to massive monorepos without slowing down your machine.

---

## 🚀 Key Features

### 🛡️ Security & Privacy
*   **Secret Redaction**: Automatically identifies and masks API keys (AWS, OpenAI), passwords, and tokens.
*   **Path Anonymization**: Replaces local system paths (`C:/Users/...`) with generic tags to protect your identity.
*   **Gitignore Compliance**: Respects your `.gitignore` rules out of the box to avoid leaking temporary files.

### 📉 Smart Optimization
*   **Code Compression**: Strips comments and excessive whitespace, reducing token count by up to 25% while preserving logic.
*   **Token Estimation**: Get accurate token counts for different models (GPT, Claude, Gemini) before you even open the AI chat.

### 🌳 Structural Intelligence
*   **Static Analysis**: Generates a project tree that doesn't just show files, but also the **Classes, Functions, and Methods** inside them using Python's AST.
*   **Contextual Separation**: Automatically categorizes files into Modules, Tests, and Resources.

### ⚙️ Professional Workflow
*   **Dual Interface**: Use the intuitive **GUI** for daily development or the **CLI** for automation and pipelines.
*   **Profiles**: Save different configurations (e.g., "Full Audit" vs "Minimal Logic") and switch between them instantly.
*   **Seamless Updates**: The app stays up to date automatically via background downloads (OTA) and integrity checks.

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
The most common way to use Transcriptor4AI. Launch it, select your folder, and get your context.

```bash
# Using the installed command
transcriptor-gui

# OR running from source (New Entrypoint)
python src/transcriptor4ai/main.py
```

*   **Simulation Mode**: Use **"SIMULATE"** to see exactly what will be sent and how many tokens it will cost without creating any files.

### 2. Command Line Interface (CLI)
For power users who need speed or want to integrate transcription into their build scripts.

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

1.  **`full_context.txt`**: The ultimate file. It contains the Tree, Modules, Tests, and Resources in one single AI-ready document.
2.  **`tree.txt`**: A clean map of your project structure.
3.  **`modules.txt / tests.txt`**: Separated logic for fine-grained control.
4.  **`errors.txt`**: A transparent log of any files that couldn't be read (e.g., permission issues).

---

## ⚙️ Configuration

Transcriptor4AI stores your preferences and profiles in a local `config.json` inside your user data folder.

**Sample Configuration:**
```json
{
    "version": "1.6.0",
    "app_settings": {
        "theme": "SystemDefault",
        "auto_check_updates": true
    },
    "last_session": {
        "target_model": "GPT-4o / GPT-5",
        "enable_sanitizer": true,
        "minify_output": true,
        "respect_gitignore": true
    }
}
```

---

## 🛠️ Development & Architecture

This project follows a **Hexagonal Architecture** to ensure maintainability and robustness:
*   **Domain**: Data models and business rules.
*   **Core**: Pipeline logic, workers, and AST analysis.
*   **Infra**: FileSystem, Logging, and Network adapters.
*   **Interface**: CLI and GUI adapters.

### Quality Assurance
Run the comprehensive test suite (Unit, Integration, E2E):
```bash
# Run the complete industrial test suite
pytest -v

# Static type analysis with strict checking
mypy src/transcriptor4ai
```

### Standalone Build
To create a standalone executable (`.exe`):
```bash
# Use the refactored build script in the scripts/ folder
python scripts/build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com