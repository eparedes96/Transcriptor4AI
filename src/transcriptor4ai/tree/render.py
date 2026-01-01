from __future__ import annotations

from typing import List

from transcriptor4ai.tree.models import Tree, FileNode
from transcriptor4ai.tree.ast_symbols import extraer_funciones_clases


# -----------------------------------------------------------------------------
# Render del árbol
# -----------------------------------------------------------------------------
def generar_estructura_texto(
    estructura: Tree,
    lines: List[str],
    prefix: str = "",
    mostrar_funciones: bool = False,
    mostrar_clases: bool = False,
    mostrar_metodos: bool = False,
) -> None:
    entries = sorted(estructura.keys())
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "
        node = estructura[entry]

        # Directorio (subárbol)
        if isinstance(node, dict):
            lines.append(prefix + connector + entry)
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

        # Archivo
        if isinstance(node, FileNode):
            lines.append(prefix + connector + entry)

            if mostrar_funciones or mostrar_clases or mostrar_metodos:
                info_fc = extraer_funciones_clases(
                    node.path,
                    mostrar_funciones=mostrar_funciones,
                    mostrar_clases=mostrar_clases,
                    mostrar_metodos=mostrar_metodos,
                )
                child_prefix = prefix + ("    " if is_last else "│   ")
                for linea_info in info_fc:
                    lines.append(child_prefix + linea_info)

            continue

        # Fallback
        lines.append(prefix + connector + entry)