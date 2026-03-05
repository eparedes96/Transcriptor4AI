from __future__ import annotations

"""
Tree Renderer Unit Tests.

Validates the recursive ASCII visualization logic of the directory tree,
ensuring proper connector placement, indentation, deterministic sorting,
and correct integration with AST symbol injection.
"""

from typing import Any, Dict, List

import pytest

from transcriptor4ai.application.analysis.tree_renderer import render_tree_structure
from transcriptor4ai.domain.entities.file_node import FileNode


# ==============================================================================
# TEST GROUP: TREE RENDERING & FORMATTING LOGIC
# ==============================================================================

@pytest.mark.unit
def test_render_tree_structure_basic_hierarchy() -> None:
    """
    Verifies that a standard nested directory structure is accurately
    rendered with correct intermediate (├──) and terminal (└──) connectors.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    tree: Dict[str, Any] = {
        "src": {
            "main.py": FileNode(path="/src/main.py"),
            "utils.py": FileNode(path="/src/utils.py")
        },
        "README.md": FileNode(path="/README.md")
    }
    lines: List[str] = []

    # 2. ACT: Execute the specific behavior/method
    render_tree_structure(tree, lines)

    # 3. ASSERT: Verify the outcome and side effects
    expected_lines = [
        "├── README.md",
        "└── src",
        "    ├── main.py",
        "    └── utils.py"
    ]

    assert lines == expected_lines


@pytest.mark.unit
def test_render_tree_structure_with_ast_symbols(mocker: Any) -> None:
    """
    Ensures that when AST flags are active, the renderer correctly queries
    the AST parser and appends the symbols with the appropriate child indentation.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    tree: Dict[str, Any] = {
        "app.py": FileNode(path="/app.py"),
        "config.json": FileNode(path="/config.json")
    }
    lines: List[str] = []

    # CRITICAL POINT: Mock the external AST parser to avoid physical file reading
    mock_extractor = mocker.patch(
        "transcriptor4ai.application.analysis.tree_renderer.extract_definitions"
    )
    mock_extractor.return_value = ["Class: Server", "Function: start()"]

    # 2. ACT: Execute the specific behavior/method
    render_tree_structure(
        tree,
        lines,
        show_classes=True,
        show_functions=True
    )

    # 3. ASSERT: Verify the outcome and side effects
    expected_lines = [
        "├── app.py",
        "│   Class: Server",
        "│   Function: start()",
        "└── config.json",
        "    Class: Server",
        "    Function: start()"
    ]

    assert lines == expected_lines
    assert mock_extractor.call_count == 2


@pytest.mark.unit
def test_render_tree_structure_alphabetical_sorting() -> None:
    """
    Validates that dictionary keys are sorted alphabetically before rendering
    to guarantee deterministic outputs regardless of insertion order.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    # Inserted out of alphabetical order
    tree: Dict[str, Any] = {
        "zebra.py": FileNode(path="/zebra.py"),
        "apple.py": FileNode(path="/apple.py"),
        "mango.py": FileNode(path="/mango.py")
    }
    lines: List[str] = []

    # 2. ACT: Execute the specific behavior/method
    render_tree_structure(tree, lines)

    # 3. ASSERT: Verify the outcome and side effects
    expected_lines = [
        "├── apple.py",
        "├── mango.py",
        "└── zebra.py"
    ]

    assert lines == expected_lines


@pytest.mark.unit
def test_render_tree_structure_handles_empty_tree() -> None:
    """
    Resilience Check: Rendering an empty dictionary should safely complete
    without modifying the lines accumulator or raising an error.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    tree: Dict[str, Any] = {}
    lines: List[str] = []

    # 2. ACT: Execute the specific behavior/method
    render_tree_structure(tree, lines)

    # 3. ASSERT: Verify the outcome and side effects
    assert lines == []
    assert len(lines) == 0


@pytest.mark.unit
def test_render_tree_structure_deep_nesting() -> None:
    """
    Verifies that deep recursion maintains correct alignment strings
    across multiple depths.
    """
    # 1. ARRANGE: Set up preconditions and mocks
    tree: Dict[str, Any] = {
        "level1": {
            "level2": {
                "level3": {
                    "file.txt": FileNode(path="/file.txt")
                }
            }
        }
    }
    lines: List[str] = []

    # 2. ACT: Execute the specific behavior/method
    render_tree_structure(tree, lines)

    # 3. ASSERT: Verify the outcome and side effects
    expected_lines = [
        "└── level1",
        "    └── level2",
        "        └── level3",
        "            └── file.txt"
    ]

    assert lines == expected_lines