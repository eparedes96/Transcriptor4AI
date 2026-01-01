from __future__ import annotations

import logging
import os
import re
from typing import Callable, List, Optional

from transcriptor4ai.filtering import (
    compile_patterns,
    default_extensiones,
    default_patrones_excluir,
    default_patrones_incluir,
    es_test,
    matches_any,
    matches_include,
)
from transcriptor4ai.tree.models import FileNode, Tree
from transcriptor4ai.tree.render import generar_estructura_texto

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def generar_arbol_directorios(
        ruta_base: str,
        modo: str = "todo",
        extensiones: Optional[List[str]] = None,
        patrones_incluir: Optional[List[str]] = None,
        patrones_excluir: Optional[List[str]] = None,
        mostrar_funciones: bool = False,
        mostrar_clases: bool = False,
        mostrar_metodos: bool = False,
        imprimir: bool = False,  # Kept for signature compatibility, but behavior changes (logs instead of prints)
        guardar_archivo: str = "",
) -> List[str]:
    """
    Generate a hierarchical text representation of the file structure.

    Optionally parses files to show symbols (functions, classes, methods).
    This service does NOT print to stdout.

    Args:
        ruta_base: Root directory to scan.
        modo: Processing mode ("todo", "solo_modulos", "solo_tests").
        extensiones: List of allowed file extensions.
        patrones_incluir: Regex patterns for inclusion.
        patrones_excluir: Regex patterns for exclusion.
        mostrar_funciones: If True, parse and show top-level functions.
        mostrar_clases: If True, parse and show top-level classes.
        mostrar_metodos: If True (and classes=True), show methods.
        imprimir: Deprecated/Legacy flag. If True, logs the tree at INFO level instead of printing.
        guardar_archivo: If provided, saves the tree to this file path.

    Returns:
        A list of strings representing the tree lines.
    """
    logger.info(f"Generating directory tree for: {ruta_base}")

    # -------------------------
    # Input Normalization
    # -------------------------
    if extensiones is None:
        extensiones = default_extensiones()
    if patrones_incluir is None:
        patrones_incluir = default_patrones_incluir()
    if patrones_excluir is None:
        patrones_excluir = default_patrones_excluir()

    ruta_base_abs = os.path.abspath(ruta_base)

    incluir_rx = compile_patterns(patrones_incluir)
    excluir_rx = compile_patterns(patrones_excluir)

    # -------------------------
    # Build Structure
    # -------------------------
    estructura = _construir_estructura(
        ruta_base_abs,
        modo=modo,
        extensiones=extensiones,
        incluir_rx=incluir_rx,
        excluir_rx=excluir_rx,
        es_test_func=es_test,
    )

    # -------------------------
    # Render Tree
    # -------------------------
    lines: List[str] = []
    generar_estructura_texto(
        estructura,
        lines,
        prefix="",
        mostrar_funciones=mostrar_funciones,
        mostrar_clases=mostrar_clases,
        mostrar_metodos=mostrar_metodos,
    )

    # -------------------------
    # Output Handling
    # -------------------------
    # Policy enforcement: Core never prints. Use logging if requested.
    if imprimir:
        logger.info("Tree Preview:\n" + "\n".join(lines))

    if guardar_archivo:
        try:
            out_dir = os.path.dirname(os.path.abspath(guardar_archivo))
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            with open(guardar_archivo, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            logger.info(f"Tree saved to file: {guardar_archivo}")
        except OSError as e:
            msg = f"Failed to save tree to '{guardar_archivo}': {e}"
            logger.error(msg)
            lines.append(f"[ERROR] {msg}")

    return lines


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------
def _construir_estructura(
        ruta_base: str,
        modo: str,
        extensiones: List[str],
        incluir_rx: List[re.Pattern],
        excluir_rx: List[re.Pattern],
        es_test_func: Callable[[str], bool],
) -> Tree:
    """Recursively build the Tree dictionary from the filesystem."""
    estructura: Tree = {}

    for root, dirs, files in os.walk(ruta_base):
        # Modify dirs in-place to prune traversal
        dirs[:] = [d for d in dirs if not matches_any(d, excluir_rx)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, ruta_base)
        if rel_root == ".":
            rel_root = ""

        # Navigate or create intermediate nodes
        nodos_carpeta: Tree = estructura
        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in nodos_carpeta or not isinstance(nodos_carpeta[p], dict):
                    nodos_carpeta[p] = {}
                # Type safe traversal
                current = nodos_carpeta[p]
                if isinstance(current, dict):
                    nodos_carpeta = current

        # Process Files
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext not in extensiones:
                continue

            # Check Patterns
            if matches_any(file_name, excluir_rx):
                continue
            if not matches_include(file_name, incluir_rx):
                continue

            # Check Mode (Tests/Modules)
            archivo_es_test = es_test_func(file_name)
            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue

            # Add File Node
            full_path = os.path.join(root, file_name)
            nodos_carpeta[file_name] = FileNode(path=full_path)

    return estructura