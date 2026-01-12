from __future__ import annotations

"""
AST Analysis Service.

Parses Python source files to extract top-level definitions (classes, functions).
Designed to be fault-tolerant: syntax errors in the user's code will not
crash the analyzer.
"""

import ast
import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def extract_definitions(
        file_path: str,
        show_functions: bool,
        show_classes: bool,
        show_methods: bool = False,
) -> List[str]:
    """
    Parse a Python file using AST to extract structural definitions.

    Args:
        file_path: Absolute path to the source file.
        show_functions: If True, include top-level functions.
        show_classes: If True, include class definitions.
        show_methods: If True, include methods inside classes.

    Returns:
        List[str]: A list of formatted strings describing the symbols found.
        Returns a descriptive error string if parsing fails.
    """
    results: List[str] = []

    # 1. Read File Content
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

    # 3. Traverse Nodes
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