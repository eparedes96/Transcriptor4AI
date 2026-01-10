# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.3.0-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is an industrial-grade context extraction engine designed to bridge the gap between complex local codebases and Large Language Models (LLMs) such as **GPT-4o**, **Claude 3.5**, or **Llama 3**.

It goes beyond simple text flattening: it provides staging-based simulation, AST-enhanced structural analysis, and a professional distribution lifecycle to ensure your AI assistant receives the most accurate and optimized context possible.

---

## 🚀 Key Features

### 🧠 Intelligent Context Orchestration
*   **Precision Token Estimator**: Real-time context size calculation using `tiktoken`. Tailored heuristics for GPT, Claude, and Gemini to prevent "Out of Context" errors.
*   **Staging Engine**: A specialized simulation mode (**Dry-Run**) that processes data in memory to provide exact statistics and token counts without touching your filesystem.
*   **Profile Architecture**: Save and switch between complex configurations (e.g., "Logic Only", "Full Audit", "DevOps Focus") with a single click.

### 🔍 Advanced Filtering & Security
*   **Native .gitignore Integration**: Full compliance with project-specific ignore rules, ensuring sensitive data and dependencies stay local.
*   **Ecosystem Stacks**: Instant configuration for **Python**, **Web Fullstack**, **Rust**, **Go**, **DevOps**, and more.
*   **Resource Classification**: Intelligent separation of source code, unit tests, and project assets (Markdown, JSON, Dockerfiles).

### 🛠️ Professional Tooling
*   **AST Symbol Mapping**: A directory tree that performs static analysis to list Classes, Functions, and Methods without execution.
*   **Dual-Mode Interface**: High-productivity GUI for developers and a robust CLI for CI/CD pipeline automation.

### 🤝 Lifecycle & Community (v1.3.0+)
*   **Smart Error Reporter**: Automatic capture of critical exceptions with an integrated diagnostic modal and one-click submission to developers.
*   **Feedback Hub**: Direct communication channel for feature requests and bug reports with automated log attachment.
*   **OTA Auto-Updates**: Seamless version tracking via GitHub API with an autonomous sidecar updater for zero-friction maintenance.

---

## 📦 Installation

### Prerequisites
*   Python 3.12 or higher.
*   Conda (Recommended).

### Setup
```bash
# Clone the repository
git clone https://github.com/eparedes96/Transcriptor4AI.git
cd Transcriptor4AI

# Update your Conda environment
conda env update --file environment.yml --prune
conda activate transcriptor4ai

# Install in editable mode
pip install -e .
```
---

## 🖥️ Usage

Transcriptor4AI provides two entry points depending on your workflow:

### 1. Graphical User Interface (GUI)
Launch the visual dashboard for manual context preparation:

```bash
transcriptor-gui
```

*   **Profiles**: Manage saved states using the top-level bar.
*   **Feedback**: Use the **Feedback Hub** to send logs or suggestions directly to the developer.
*   **Simulation**: Use **"SIMULATE"** to validate paths and see projected metrics without writing to disk.

### 2. Command Line Interface (CLI)
Ideal for automation, remote servers, or power users.

**Basic Example:**
```bash
transcriptor-cli -i ./my_project -o ./dist --resources --tree
```

**Advanced Example (Resources + Unified Output + AST):**
```bash
transcriptor-cli -i ./src \
                 -o ./dist \
                 --unified-only \
                 --tree --classes --functions --methods \
                 --ext .py,.js,.sql \
                 --dry-run
```
---

## ⚙️ Configuration

The application maintains a hierarchical state in a `config.json` file located in your user data directory (`%LOCALAPPDATA%` on Windows or `~/.transcriptor4ai` on Linux).

**Example Structure:**

```json
{
    "version": "1.3.0",
    "app_settings": {
        "theme": "SystemDefault",
        "auto_check_updates": true,
        "allow_telemetry": true
    },
    "last_session": {
        "target_model": "GPT-4o / GPT-5",
        "respect_gitignore": true,
        "generate_tree": true
    },
    "saved_profiles": {
        "Fast Scan": { "extensions": [".py"], "generate_tree": false }
    }
}
```

---

## 📂 Output Structure

The engine generates a structured output directory with the following artifacts:

1.  **`{prefix}_full_context.txt`**: The "Master Context". Tree + Modules + Tests + Resources in a single AI-optimized file.
2.  **`{prefix}_tree.txt`**: Hierarchical project map with optional AST symbol definitions.
3.  **`{prefix}_modules.txt / tests.txt / resources.txt`**: Granular components for selective context injection.
4.  **`{prefix}_errors.txt`**: Detailed log of files skipped due to encoding or permission issues.

---

## 🛠️ Development & Build

### Quality Assurance
```bash
# Run the full suite
pytest

# Technical coverage
pytest -v --strict-markers
```

### Standalone Distribution
To generate the production-ready executable:
```bash
# Building the standalone bundle (PyInstaller)
python build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com