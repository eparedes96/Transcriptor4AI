from __future__ import annotations

"""
Unit tests for the Directory Tree Generator.

Verifies hierarchical structure building, file filtering logic within the tree,
and the integration of AST symbols in the output.
"""

import pytest
from transcriptor4ai.core.analysis.tree_generator import generate_directory_tree, _build_structure
from transcriptor4ai.core.pipeline.filters import compile_patterns, is_test
from transcriptor4ai.domain.tree_models import FileNode


@pytest.fixture
def project_structure(tmp_path):
    """
    Creates a temporary directory structure for testing tree generation.

    Structure:
    /root
      /src
        main.py
        utils.py
      /tests
        test_main.py
      /ignore_me
        secret.py
      README.md
    """
    root = tmp_path / "root"
    root.mkdir()

    src = root / "src"
    src.mkdir()
    (src / "main.py").write_text("class Main: pass", encoding="utf-8")
    (src / "utils.py").write_text("def helper(): pass", encoding="utf-8")

    tests = root / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_one(): pass", encoding="utf-8")

    ignore = root / "ignore_me"
    ignore.mkdir()
    (ignore / "secret.py").write_text("SECRET = 1", encoding="utf-8")

    (root / "README.md").write_text("# Docs", encoding="utf-8")

    return root


def test_build_structure_recursive_logic(project_structure):
    """Verify that _build_structure correctly maps the filesystem to a dict."""
    input_path = str(project_structure)
    extensions = [".py", ".md"]
    include_patterns = [r".*"]
    exclude_patterns = [r"ignore_me"]

    structure = _build_structure(
        input_path=input_path,
        mode="all",
        extensions=extensions,
        include_patterns_rx=compile_patterns(include_patterns),
        exclude_patterns_rx=compile_patterns(exclude_patterns),
        test_detect_func=is_test
    )

    # Check root level
    assert "src" in structure
    assert "tests" in structure
    assert "README.md" in structure
    assert "ignore_me" not in structure

    # Check nested levels (FileNode objects)
    assert isinstance(structure["src"], dict)
    assert isinstance(structure["src"]["main.py"], FileNode)
    assert structure["src"]["main.py"].path.endswith("main.py")


def test_generate_directory_tree_output_format(project_structure):
    """Verify the final string output of the tree generator."""
    lines = generate_directory_tree(
        input_path=str(project_structure),
        mode="all",
        extensions=[".py"],
        exclude_patterns=[r"ignore_me", r"README.md"],
        show_classes=True
    )

    output = "\n".join(lines)

    # Structure checks (Using standard connectors used in renderer)
    assert "├── src" in output
    assert "│   ├── main.py" in output
    assert "└── tests" in output

    # AST integration check (Classes enabled)
    assert "Class: Main" in output

    # Exclusions
    assert "ignore_me" not in output
    assert "README.md" not in output


def test_generate_directory_tree_modes(project_structure):
    """
    Verify that 'modules_only' and 'tests_only' modes filter files correctly.
    Crucial: Empty directories (after filtering) should be pruned.
    """
    # 1. Modules Only
    lines_modules = generate_directory_tree(
        input_path=str(project_structure),
        mode="modules_only",
        extensions=[".py"],
        exclude_patterns=[r"ignore_me"]
    )
    out_modules = "\n".join(lines_modules)

    assert "main.py" in out_modules
    assert "test_main.py" not in out_modules
    assert "tests" not in out_modules

    # 2. Tests Only
    lines_tests = generate_directory_tree(
        input_path=str(project_structure),
        mode="tests_only",
        extensions=[".py"],
        exclude_patterns=[r"ignore_me"]
    )
    out_tests = "\n".join(lines_tests)

    assert "test_main.py" in out_tests
    assert "src" not in out_tests


def test_generate_directory_tree_save_file(project_structure):
    """Verify that the tree is saved to a file if save_path is provided."""
    save_file = project_structure / "tree_output.txt"

    generate_directory_tree(
        input_path=str(project_structure),
        save_path=str(save_file),
        extensions=[".py"]
    )

    assert save_file.exists()
    content = save_file.read_text(encoding="utf-8")
    assert "src" in content
    assert "main.py" in content