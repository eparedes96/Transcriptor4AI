from __future__ import annotations

"""
Tree Renderer.

Converts a recursive Tree dictionary structure into a visual string representation.
Delegates to the AST parser for symbol extraction on leaf nodes.
"""

from typing import List

from transcriptor4ai.core.analysis.ast_parser import extract_definitions
from transcriptor4ai.domain.tree_models import FileNode, Tree


def render_tree_structure(
        tree_structure: Tree,
        lines: List[str],
        prefix: str = "",
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
) -> None:
    """
    Recursively render the tree structure into a list of strings.

    Args:
        tree_structure: The current level of the tree dictionary.
        lines: The list accumulator for output lines.
        prefix: The indentation string for the current level.
        show_functions: Flag to enable function display.
        show_classes: Flag to enable class display.
        show_methods: Flag to enable method display.
    """
    entries = sorted(tree_structure.keys())
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        node = tree_structure[entry]

        # Case A: Directory (Recursion)
        if isinstance(node, dict):
            lines.append(f"{prefix}{connector}{entry}")
            new_prefix = prefix + ("    " if is_last else "│   ")
            render_tree_structure(
                node,
                lines,
                prefix=new_prefix,
                show_functions=show_functions,
                show_classes=show_classes,
                show_methods=show_methods,
            )
            continue

        # Case B: File (Leaf)
        if isinstance(node, FileNode):
            lines.append(f"{prefix}{connector}{entry}")

            # AST Analysis Integration
            if show_functions or show_classes or show_methods:
                symbols = extract_definitions(
                    node.path,
                    show_functions=show_functions,
                    show_classes=show_classes,
                    show_methods=show_methods,
                )

                # Indent symbols below the file
                child_prefix = prefix + ("    " if is_last else "│   ")
                for item in symbols:
                    lines.append(f"{child_prefix}{item}")

            continue

        # Case C: Fallback (Just name)
        lines.append(f"{prefix}{connector}{entry}")