from __future__ import annotations

from typing import List

from transcriptor4ai.tree.ast_symbols import extract_definitions
from transcriptor4ai.tree.models import FileNode, Tree


# -----------------------------------------------------------------------------
# Tree Rendering Logic
# -----------------------------------------------------------------------------
def generar_estructura_texto(
        estructura: Tree,
        lines: List[str],
        prefix: str = "",
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
) -> None:
    """
    Recursive function to render the dictionary structure into a list of strings.

    Args:
        estructura: The Tree dictionary (current level).
        lines: The accumulator list for output lines.
        prefix: Indentation string for the current level.
        show_functions: Flag to enable function parsing.
        show_classes: Flag to enable class parsing.
        show_methods: Flag to enable method parsing.
    """
    entries = sorted(estructura.keys())
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        node = estructura[entry]

        # Case A: Directory (Sub-tree)
        if isinstance(node, dict):
            lines.append(f"{prefix}{connector}{entry}")
            new_prefix = prefix + ("    " if is_last else "│   ")
            generar_estructura_texto(
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

            # Optional AST analysis
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

        # Case C: Fallback (Should not happen with correct types)
        lines.append(f"{prefix}{connector}{entry}")