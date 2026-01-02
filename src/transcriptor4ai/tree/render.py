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
        mostrar_funciones: bool = False,
        mostrar_clases: bool = False,
        mostrar_metodos: bool = False,
) -> None:
    """
    Recursive function to render the dictionary structure into a list of strings.

    Args:
        estructura: The Tree dictionary (current level).
        lines: The accumulator list for output lines.
        prefix: Indentation string for the current level.
        mostrar_funciones: Flag to enable function parsing.
        mostrar_clases: Flag to enable class parsing.
        mostrar_metodos: Flag to enable method parsing.
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
                mostrar_funciones=mostrar_funciones,
                mostrar_clases=mostrar_clases,
                mostrar_metodos=mostrar_metodos,
            )
            continue

        # Case B: File (Leaf)
        if isinstance(node, FileNode):
            lines.append(f"{prefix}{connector}{entry}")

            # Optional AST analysis
            if mostrar_funciones or mostrar_clases or mostrar_metodos:
                symbols = extract_definitions(
                    node.path,
                    show_functions=mostrar_funciones,
                    show_classes=mostrar_clases,
                    show_methods=mostrar_metodos,
                )

                # Indent symbols below the file
                child_prefix = prefix + ("    " if is_last else "│   ")
                for item in symbols:
                    lines.append(f"{child_prefix}{item}")

            continue

        # Case C: Fallback (Should not happen with correct types)
        lines.append(f"{prefix}{connector}{entry}")