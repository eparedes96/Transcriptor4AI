from __future__ import annotations

"""
AST Analysis Service.

Provides fault-tolerant parsing of Python source files to extract structural 
definitions such as classes, functions, and methods. Designed to assist 
LLMs in understanding code architecture without full file transcription.
"""

import ast
import logging
import os
from typing import List

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def extract_definitions(
        file_path: str,
        show_functions: bool,
        show_classes: bool,
        show_methods: bool = False,
) -> List[str]:
    """
    Parse a Python file using the Abstract Syntax Tree (AST) module.

    Safely extracts top-level and nested definitions based on provided
    filtering flags. Handles I/O and syntax errors gracefully to prevent
    pipeline interruption.

    Args:
        file_path: Absolute path to the source file to analyze.
        show_functions: Whether to include top-level functions in the result.
        show_classes: Whether to include class definitions in the result.
        show_methods: Whether to include methods inside classes.

    Returns:
        List[str]: Formatted descriptors of the symbols found.
                   Returns an error message if parsing fails.
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

    # 2. Parse AST Structure
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

    # 3. Traverse Nodes and Extract Symbols
    for node in tree.body:
        # -- Global Functions --
        if show_functions and isinstance(node, ast.FunctionDef):
            results.append(f"Function: {node.name}()")

        # -- Class Definitions --
        if show_classes and isinstance(node, ast.ClassDef):
            results.append(f"Class: {node.name}")

            # -- Class Methods (Optional deep inspection) --
            if show_methods:
                methods = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        methods.append(child.name)

                for m in methods:
                    results.append(f"  Method: {m}()")

    return results