from __future__ import annotations

"""
Tree Rendering Service.

Transforms hierarchical Tree models into visual ASCII representations. 
Manages recursion depth, line connectors, and integrates with AST services 
to display code symbols (classes/functions) as nested leaf elements.
"""

import logging
from typing import List

from transcriptor4ai.application.analysis.ast_parser import extract_definitions
from transcriptor4ai.domain.entities.file_node import FileNode, Tree

# Global logger for rendering diagnostics
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API
# ==============================================================================

def render_tree_structure(
        tree_structure: Tree,
        lines: List[str],
        prefix: str = "",
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
) -> None:
    """
    Recursively transform the Tree model into a list of ASCII-formatted strings.

    Args:
        tree_structure: The recursive dictionary model to process.
        lines: Accumulator list where formatted strings are appended.
        prefix: Current indentation and connector prefix for recursion.
        show_functions: Enable function symbol extraction.
        show_classes: Enable class symbol extraction.
        show_methods: Enable method symbol extraction.
    """
    # 1. PREPARE: Sort entries to ensure deterministic tree output
    # Critical to prevent visual diffs between runs on identical structures
    entries = sorted(tree_structure.keys())
    total = len(entries)

    # 2. ITERATE: Process each node in the current directory level
    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        node = tree_structure[entry]

        # Scenario A: NODE IS A DIRECTORY
        if isinstance(node, dict):
            lines.append(f"{prefix}{connector}{entry}")

            # Calculate new prefix for child elements
            new_prefix = prefix + ("    " if is_last else "│   ")

            # Recursive call to process subdirectory
            render_tree_structure(
                node,
                lines,
                prefix=new_prefix,
                show_functions=show_functions,
                show_classes=show_classes,
                show_methods=show_methods,
            )
            continue

        # Scenario B: NODE IS A FILE (FileNode)
        if isinstance(node, FileNode):
            lines.append(f"{prefix}{connector}{entry}")

            # 3. ANALYSIS: Inject AST symbols if requested
            if show_functions or show_classes or show_methods:
                symbols = extract_definitions(
                    node.path,
                    show_functions=show_functions,
                    show_classes=show_classes,
                    show_methods=show_methods,
                )

                # Indent symbols as nested children of the file node
                child_prefix = prefix + ("    " if is_last else "│   ")
                for item in symbols:
                    lines.append(f"{child_prefix}{item}")

            continue

        # Scenario C: FALLBACK for unclassified or malformed nodes
        lines.append(f"{prefix}{connector}{entry}")