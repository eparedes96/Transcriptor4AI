from __future__ import annotations

import ast
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# AST Symbol Extraction
# -----------------------------------------------------------------------------
def extract_definitions(
        file_path: str,
        show_functions: bool,
        show_classes: bool,
        show_methods: bool = False,
) -> List[str]:
    """
    Parse a Python file using AST to extract top-level definitions.

    Args:
        file_path: Absolute path to the file.
        show_functions: Whether to list top-level functions.
        show_classes: Whether to list classes.
        show_methods: Whether to list methods inside classes.

    Returns:
        A list of formatted strings to be rendered in the tree.
        Returns error messages as strings if parsing fails, ensuring the tree
        visualizes the issue rather than crashing.
    """
    results: List[str] = []

    # 1. Read File
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError) as e:
        msg = f"[ERROR] Could not read '{os.path.basename(file_path)}': {e}"
        logger.debug(msg)
        return [msg]

    # 2. Parse AST
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        msg = f"[ERROR] Invalid AST (SyntaxError): {e.msg} (line {e.lineno})"
        logger.debug(f"Syntax error in {file_path}: {e}")
        return [msg]
    except Exception as e:
        msg = f"[ERROR] AST Parsing failed: {e}"
        logger.warning(f"Unexpected AST error in {file_path}: {e}")
        return [msg]

    # 3. Walk Nodes
    for node in tree.body:
        # -- Functions --
        if show_functions and isinstance(node, ast.FunctionDef):
            results.append(f"Function: {node.name}()")

        # -- Classes --
        if show_classes and isinstance(node, ast.ClassDef):
            results.append(f"Class: {node.name}")

            # -- Methods --
            if show_methods:
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append(child.name)

                for m in methods:
                    results.append(f"  Method: {m}()")

    return results