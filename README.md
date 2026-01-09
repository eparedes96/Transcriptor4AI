# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.3.0.-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is an industrial-grade context extraction tool designed for the AI era. It prepares entire codebases for Large Language Models (LLMs) like **GPT-4o**, **Claude 3.5**, or **Llama 3**.

It goes beyond simple text flattening: it provides intelligent token estimation, AST-enhanced directory trees, and resource management, creating a single, optimized context file (`_full_context.txt`) ready for your prompt window.

---

## 🚀 Key Features

### 🧠 Smart Context Management
*   **Token Estimator**: Real-time estimation of context size using `tiktoken`. Select your target model (GPT, Claude, Llama) to get precise counts before sending data.
*   **Profile Manager**: Save, load, and delete named configurations (e.g., "Backend Only", "Full Documentation").
*   **Session Persistence**: The application automatically saves your state on exit. Pick up exactly where you left off.

### 🔍 Advanced Filtering & Security
*   **Native .gitignore**: Automatically respects your project's ignore rules. No more accidental `node_modules` or secrets in your context.
*   **Resource Processing**: First-class support for non-code assets. Include `README.md`, `.json` configs, `.yaml` workflows, and `Dockerfiles`.
*   **Extension Stacks**: One-click configuration for ecosystems like **Python**, **Web**, **C#/.NET**, **Rust**, **Go**, and **DevOps**.

### 🛠️ Core Capabilities
*   **Flexible Output**: Generate a **Unified Context File** for easy copy-pasting or individual components for documentation.
*   **AST Analysis**: Visual directory tree that "sees inside" files, listing Classes, Functions, and Methods without executing code.
*   **Dual Interface**: A modern GUI for visual workflows and a powerful CLI for CI/CD automation.

---

## 📦 Installation

### Prerequisites
*   Python 3.12 or higher.

### From Source (Recommended)
Since this project uses a modern `src` layout, install it using `pip` to ensure dependencies and entry points are correctly configured.

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/transcriptor4ai.git
cd transcriptor4ai

# 2. Install dependencies and the package
pip install .

# For development (editable mode)
pip install -e .
```

---

## 🖥️ Usage

Once installed, two commands become available in your terminal:

### 1. Graphical User Interface (GUI)
Launch the visual tool:

```bash
transcriptor-gui
```

*   **Profiles**: Use the top bar to Load/Save specific configurations.
*   **Stacks**: Select "Python Data" or "Web Fullstack" to auto-fill extensions.
*   **Target Model**: Choose your destination LLM (e.g., GPT-4o) for accurate token counts.
*   **Simulation**: Use **"SIMULATE"** to validate paths and see the projected file list and token count without writing to disk.

### 2. Command Line Interface (CLI)
Ideal for scripts, automation, or quick operations.

**Basic Example:**

```bash
transcriptor-cli -i ./my_project -o ./dist --resources --tree
```

**Advanced Example (Resources + Unified Output):**

```bash
transcriptor-cli -i ./src \
                 -o ./output \
                 --unified-only \
                 --resources \
                 --tree --classes --functions \
                 --dry-run
```

#### CLI Arguments Reference

| Flag | Description |
| :--- | :--- |
| `-i`, `--input` | Path to the source directory to process. |
| `-o`, `--output-base` | Base output directory. |
| `--resources` | Include resource files (docs, config, data). |
| `--no-gitignore` | Disable `.gitignore` parsing (read everything). |
| `--unified-only` | Generate ONLY the single `_full_context.txt` file. |
| `--tree` | Generate the directory tree structure. |
| `--classes` | Include class definitions in the tree. |
| `--functions` | Include function definitions in the tree. |
| `--ext` | Comma-separated extensions (e.g., `.py,.js`). |
| `--dry-run` | Simulate execution and show **Token Estimate**. |

Use `transcriptor-cli --help` for the full list of options.

---

## ⚙️ Configuration

The application uses a `config.json` file for persistent settings and profiles.
*   **Location**: OS User Data Directory (e.g., `%LOCALAPPDATA%\Transcriptor4AI` on Windows).
*   **Structure**: Hierarchical JSON storing `app_settings`, `last_session`, and `saved_profiles`.

**Example Structure:**

```json
{
    "version": "1.3.0.",
    "last_session": {
        "process_modules": true,
        "process_resources": true,
        "respect_gitignore": true,
        "target_model": "GPT-4o / GPT-5",
        "extensions": [".py", ".md", ".json"],
        "generate_tree": true
    },
    "saved_profiles": {
        "Backend Only": { },
        "Full Documentation": { }
    }
}
```

---

## 📂 Output Structure

The output folder will contain (depending on configuration):

1.  **`{prefix}_full_context.txt`**: The master file (Tree + Scripts + Tests + Resources). **This is what you feed the AI.**
2.  **`{prefix}_resources.txt`**: Consolidated documentation and config files.
3.  **`{prefix}_modules.txt`**: Consolidated source code.
4.  **`{prefix}_tests.txt`**: Consolidated test files.
5.  **`{prefix}_tree.txt`**: Hierarchical view of the project structure.

---

## 🛠️ Development

### Running Tests
The project includes a comprehensive test suite using `pytest`.

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v
```

### Building Executable
To generate a standalone `.exe` file (Windows) or binary (Linux/Mac):

```bash
# 1. Install build tools
pip install pyinstaller

# 2. Run the build script
python build.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com