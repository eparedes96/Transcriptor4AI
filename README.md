# Transcriptor4AI

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-1.1.1-orange.svg)]()
[![Status](https://img.shields.io/badge/status-stable-green.svg)]()
[![Checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![License](https://img.shields.io/badge/license-MIT-lightgrey.svg)]()

**Transcriptor4AI** is a robust tool designed to prepare codebases for Large Language Models (LLMs) like ChatGPT, Claude, or Copilot.

It flattens complex project structures into consolidated text files and generates detailed directory trees with AST analysis (Classes, Functions, Methods), making it effortless to provide context to AI assistants.

## 🚀 Features

*   **Flexible Output**: Choose between individual files (separated by type) or a **Unified Context File** (`_full_context.txt`) ready to copy-paste into an LLM.
*   **Granular Control**: Select exactly what to include: Source Modules, Tests, and/or Directory Tree.
*   **AST Analysis**: Generates a visual directory tree that "sees inside" files, listing Classes, Functions, and Methods without executing code.
*   **Dual Interface**:
    *   **GUI**: Modern interface with a **Simulation Mode**, interactive results window (Open Folder / Copy to Clipboard), and threaded processing.
    *   **CLI**: Powerful command-line interface for automation and CI/CD pipelines.
*   **Intelligent Filtering**: Regex-based inclusion/exclusion patterns (ignores `.git`, `__pycache__` by default).
*   **Robustness**: Thread-safe execution, lazy error logging, and input sanitization.
*   **Internationalization (i18n)**: Built-in support for multiple languages (Default: English).

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

*   **Content Selection**: Check "Include Modules", "Include Tests", or "Directory Tree".
*   **Output Format**: Choose "Individual Files", "Unified Context File", or both.
*   **Simulation**: Use the blue **"SIMULATE"** button to validate paths and see what would be generated without writing to disk.
*   **Results**: After processing, use the "Copy Unified Output" button to grab the entire context immediately.

### 2. Command Line Interface (CLI)
Ideal for scripts or quick operations.

**Basic Example:**

```bash
transcriptor-cli -i ./my_project -o ./dist --tree --unified-only
```

**Advanced Example (Unified Output Only):**

```bash
transcriptor-cli -i ./src \
                 -o ./output \
                 --unified-only \
                 --tree --classes --functions \
                 --exclude "venv,tests" \
                 --json
```

#### CLI Arguments Reference

| Flag | Description |
| :--- | :--- |
| `-i`, `--input` | Path to the source directory to process. |
| `-o`, `--output-base` | Base output directory (a subdirectory is created inside). |
| `--unified-only` | **New**: Generate ONLY the single `_full_context.txt` file. |
| `--individual-only` | **New**: Generate ONLY separate files (`_modules.txt`, etc.). |
| `--no-modules` | **New**: Skip source code processing (enabled by default). |
| `--no-tests` | **New**: Skip test file processing (enabled by default). |
| `--tree` | Generate the directory tree structure. |
| `--classes` | Include class definitions in the tree. |
| `--functions` | Include function definitions in the tree. |
| `--ext` | Comma-separated extensions (e.g., `.py,.js`). |
| `--exclude` | Regex patterns to ignore (e.g., `venv,node_modules`). |
| `--dry-run` | Simulate execution without writing files. |
| `--json` | Output execution result in JSON format (useful for piping). |

Use `transcriptor-cli --help` for the full list of options.

---

## ⚙️ Configuration

The application uses a `config.json` file for persistent settings.
*   **Location**: The file is created in the working directory after the first "Save" in the GUI.
*   **Defaults**: Smart defaults are applied if the file is missing.

**Example `config.json` (v1.1.1):**

```json
{
    "process_modules": true,
    "process_tests": true,
    "create_individual_files": true,
    "create_unified_file": true,
    "extensions": [".py", ".ts"],
    "exclude_patterns": [
        "^__init__\\.py$",
        "^(__pycache__|\\.git|node_modules)$"
    ],
    "generate_tree": true,
    "show_classes": true,
    "save_error_log": true
}
```

---

## 📂 Output Structure

After running the tool, the output folder will contain (depending on your selection):

1.  **`{prefix}_full_context.txt`**: The master file containing Tree + Scripts + Tests (Ideal for LLMs).
2.  **`{prefix}_modules.txt`**: Consolidated source code (non-test files).
3.  **`{prefix}_tests.txt`**: Consolidated test files (files matching `test_*.py` or `*_test.py`).
4.  **`{prefix}_tree.txt`**: Hierarchical view of the project structure.
5.  **`{prefix}_errors.txt`**: (Optional) Log of files that could not be read.

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
# Install build tools
pip install pyinstaller

# Generate executable (One-File mode)
pyinstaller --name "transcriptor4ai" \
            --onefile \
            --noconsole \
            --add-data "src/transcriptor4ai/locales/*.json;transcriptor4ai/locales" \
            src/transcriptor4ai/main.py
```

---

## 📝 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Author**: Enrique Paredes
**Contact**: eparedesbalen@gmail.com