# tests/test_tree.py
import pytest
import os
from transcriptor4ai.tree.ast_symbols import extract_definitions
from transcriptor4ai.tree.models import FileNode, Tree
from transcriptor4ai.tree.render import generar_estructura_texto


# -----------------------------------------------------------------------------
# 1. AST Symbol Extraction Tests
# -----------------------------------------------------------------------------

def test_extract_definitions_finds_classes_and_functions(tmp_path):
    """
    Verify that the AST parser correctly identifies classes, functions, and methods.
    We use tmp_path to create a real physical file for the parser to read.
    """
    # Create a dummy python file
    content = """
class MyClass:
    def my_method(self):
        pass

def my_function():
    pass
"""
    f = tmp_path / "dummy.py"
    f.write_text(content, encoding="utf-8")

    # Run extraction
    results = extract_definitions(
        str(f),
        show_functions=True,
        show_classes=True,
        show_methods=True
    )

    # Assertions based on English outputs (Refactored logic)
    assert "Class: MyClass" in results
    assert "Function: my_function()" in results
    # Methods are indented with 2 spaces in the implementation
    assert any("Method: my_method()" in r for r in results)


def test_extract_definitions_handles_syntax_error(tmp_path):
    """The parser should not crash on invalid python code."""
    f = tmp_path / "broken.py"
    f.write_text("def broken_code( :", encoding="utf-8")

    results = extract_definitions(str(f), True, True)

    # Should return a list containing an error string, not raise Exception
    assert len(results) == 1
    assert "[ERROR]" in results[0]


# -----------------------------------------------------------------------------
# 2. Tree Rendering Logic Tests
# -----------------------------------------------------------------------------

def test_render_flat_structure():
    """Verify simple file list rendering."""
    # Mock structure: { "file1.txt": FileNode... }
    structure = {
        "file1.txt": FileNode(path="/tmp/file1.txt"),
        "file2.txt": FileNode(path="/tmp/file2.txt")
    }
    lines = []
    generar_estructura_texto(structure, lines)

    assert len(lines) == 2
    assert "├── file1.txt" in lines[0]
    assert "└── file2.txt" in lines[1]


def test_render_nested_structure():
    """Verify nested directory rendering."""
    # Mock structure: folder/ -> file.txt
    structure = {
        "folder": {
            "file.txt": FileNode(path="/tmp/folder/file.txt")
        }
    }
    lines = []
    generar_estructura_texto(structure, lines)

    assert len(lines) == 2
    assert "└── folder" in lines[0]
    assert "    └── file.txt" in lines[1]


def test_render_with_ast_flags_enabled(tmp_path):
    """
    Verify rendering passes correctly when AST flags are True.
    This catches variable naming errors inside the conditional block.
    """
    # Create a real file so extract_definitions doesn't fail
    f = tmp_path / "test_cls.py"
    f.write_text("class MyTestClass: pass", encoding="utf-8")

    structure = {
        "test_cls.py": FileNode(path=str(f))
    }

    lines = []
    # Force entry into the AST block
    generar_estructura_texto(
        structure,
        lines,
        show_classes=True
    )

    assert any("test_cls.py" in l for l in lines)
    assert any("Class: MyTestClass" in l for l in lines)