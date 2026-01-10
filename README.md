# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.4.0-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is an industrial-grade context extraction engine designed to bridge the gap between complex local codebases and Large Language Models (LLMs) such as **GPT-4o**, **Claude 3.5**, or **Gemini Pro**.

It goes beyond simple text flattening: it provides a multi-stage transformation pipeline featuring security sanitization, code optimization, and AST-enhanced structural analysis to ensure your AI assistant receives the most accurate, secure, and token-efficient context possible.

---

## 🚀 Key Features

### 🧠 Intelligent Context Orchestration
*   **Precision Token Estimator**: Real-time context size calculation using `tiktoken`. Tailored heuristics for GPT, Claude, and Gemini to prevent context overflow errors.
*   **Staging Engine**: A specialized simulation mode (**Dry-Run**) that processes data in memory to provide exact statistics and token counts without modifying your filesystem.
*   **Profile Architecture**: Save and switch between complex configurations (e.g., "Logic Only", "Full Audit", "Clean Context") with a single click.

### 🛡️ Privacy & Security Shield
*   **Secrets Sanitizer**: Automatic detection and redaction of API Keys (OpenAI, AWS, GitHub), passwords, emails, and IP addresses using high-performance Regex patterns.
*   **Path Anonymization**: Dynamically identifies local user home directories and usernames, replacing them with `<USER_HOME>` or `<USER>` tags to protect developer identity.
*   **Native .gitignore Integration**: Full compliance with project-specific ignore rules, ensuring sensitive data and heavy dependencies (like `node_modules`) stay local.

### ⚡ Context Optimization
*   **Code Minification**: Advanced filter to strip single-line and inline comments, and collapse redundant whitespace. Reduces token consumption by up to 25% without breaking code logic.
*   **Resource Classification**: Intelligent separation of source code, unit tests, and project documentation (Markdown, JSON, Config files).

### 🛠️ Professional Tooling
*   **AST Symbol Mapping**: A directory tree generator that performs static analysis to list Classes, Functions, and Methods (with parameters) directly in the project structure.
*   **Dual-Mode Interface**: High-productivity GUI for manual workflow and a robust CLI for automation and CI/CD pipelines.

### 🤝 Maintenance & Reliability
*   **Smart Error Reporter**: Automatic capture of critical exceptions with an integrated diagnostic modal and one-click submission to developers.
*   **OTA Auto-Updates**: Seamless version tracking via GitHub API with an autonomous sidecar updater featuring SHA-256 integrity verification.

---

## 📦 Installation

### Prerequisites
*   Python 3.12 or higher.
*   Conda (Recommended for dependency management).

### Setup
```bash
# Clone the repository
git clone https://github.com/eparedes96/Transcriptor4AI.git
cd Transcriptor4AI

# Create and activate the environment
conda env update --file environment.yml --prune
conda activate transcriptor4ai

# Install the package in editable mode
pip install -e .
```

---

## 🖥️ Usage

### 1. Graphical User Interface (GUI)
The primary dashboard for preparing AI context visually:

```bash
transcriptor-gui
```

*   **Profiles**: Use the top-level bar to manage saved configurations.
*   **Stack Selection**: Instant extension presets for Python, Web Fullstack, Rust, Go, and more.
*   **Simulation**: Use **"SIMULATE"** to validate filters and see projected token metrics before writing files.

### 2. Command Line Interface (CLI)
Designed for power users and automation scripts.

**Basic Example:**
```bash
transcriptor-cli -i ./my_project -o ./output --resources --tree
```

**Advanced Security & Optimization Example:**
```bash
transcriptor-cli -i ./src \
                 -o ./output \
                 --unified-only \
                 --tree --classes --functions \
                 --minify --sanitize \
                 --ext .py,.js \
                 --dry-run
```
---

## ⚙️ Configuration

The application maintains a hierarchical state in a `config.json` file located in your user data directory (`%LOCALAPPDATA%` on Windows or `~/.transcriptor4ai` on Linux).

**Example Structure:**

```json
{
    "version": "1.4.0",
    "app_settings": {
        "theme": "SystemDefault",
        "auto_check_updates": true,
        "allow_telemetry": true
    },
    "last_session": {
        "target_model": "GPT-4o / GPT-5",
        "enable_sanitizer": true,
        "minify_output": false,
        "respect_gitignore": true
    },
    "saved_profiles": {
        "Production Audit": {
            "minify_output": true,
            "enable_sanitizer": true,
            "process_resources": true
        }
    }
}
```

---

## 📂 Output Artifacts

The engine generates a structured output directory containing:

1.  **`{prefix}_full_context.txt`**: The "Master Context". Tree + Modules + Tests + Resources in a single AI-optimized file.
2.  **`{prefix}_tree.txt`**: Hierarchical project map with optional AST symbol definitions.
3.  **`{prefix}_modules.txt / tests.txt / resources.txt`**: Granular components for selective context injection.
4.  **`{prefix}_errors.txt`**: Detailed log of files skipped due to encoding or permission issues.

---

## 🛠️ Development & Build

### Quality Assurance
```bash
# Run the complete test suite
pytest -v

# Run with type checking
mypy src/transcriptor4ai
```

### Standalone Distribution
To generate the production-ready executable for Windows/Linux:
```bash
# Compile to a standalone one-file executable
python build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com