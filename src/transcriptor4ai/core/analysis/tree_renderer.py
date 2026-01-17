from __future__ import annotations

"""
Tree Renderer.

Converts recursive Tree models into visual ASCII representations. 
Handles symbol indentation and integrates with AST definition extraction.
"""

from typing import List

from transcriptor4ai.core.analysis.ast_parser import extract_definitions
from transcriptor4ai.domain.tree_models import FileNode, Tree

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def render_tree_structure(
        tree_structure: Tree,
        lines: List[str],
        prefix: str = "",
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
) -> None:
    """
    Recursively transform the Tree model into a list of strings.

    Uses standard ASCII connectors (├──, └──) and manages indentation
    levels for nested directories and AST symbols.

    Args:
        tree_structure: Current Tree node to process.
        lines: Accumulator list for output strings.
        prefix: Indentation prefix for the current recursion level.
        show_functions: Enable AST function display.
        show_classes: Enable AST class display.
        show_methods: Enable AST method display.
    """
    entries = sorted(tree_structure.keys())
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        node = tree_structure[entry]

        # Scenario A: Node is a Directory (Dictionary)
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

        # Scenario B: Node is a File (FileNode)
        if isinstance(node, FileNode):
            lines.append(f"{prefix}{connector}{entry}")

            # AST definitions injection if any flag is enabled
            if show_functions or show_classes or show_methods:
                symbols = extract_definitions(
                    node.path,
                    show_functions=show_functions,
                    show_classes=show_classes,
                    show_methods=show_methods,
                )

                # Indent symbols as children of the file entry
                child_prefix = prefix + ("    " if is_last else "│   ")
                for item in symbols:
                    lines.append(f"{child_prefix}{item}")

            continue

        # Scenario C: Fallback for unclassified nodes
        lines.append(f"{prefix}{connector}{entry}")