from __future__ import annotations

"""
AST Analysis Service.

Provides fault-tolerant parsing of Python source files to extract structural 
definitions and generate code skeletons. Supports 'Skeleton Mode' by stripping 
function bodies while preserving signatures and docstrings for LLM context optimization.
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


def generate_skeleton_code(source: str) -> str:
    """
    Transform Python source code into a structural skeleton.

    Reduces token consumption by replacing the bodies of all functions and
    methods with 'pass' or an ellipsis, while preserving class structures,
    function signatures, and original docstrings.

    Args:
        source: The original Python source code string.

    Returns:
        str: The skeletonized source code, or a fallback message if parsing fails.
    """
    try:
        # Parse the source into an AST
        tree = ast.parse(source)

        # Apply the transformation
        transformer = _SkeletonTransformer()
        skeleton_tree = transformer.visit(tree)

        # Fix locations and unparse back to source (Python 3.9+)
        ast.fix_missing_locations(skeleton_tree)
        return ast.unparse(skeleton_tree)

    except SyntaxError as e:
        logger.warning(f"Skeletonization failed due to SyntaxError: {e}")
        return f"# [SKIPPING SKELETON] File has syntax errors: {e}\n"
    except Exception as e:
        logger.error(f"Unexpected error during skeletonization: {e}")
        return f"# [ERROR] AST skeletonization failed: {str(e)}\n"


# -----------------------------------------------------------------------------
# PRIVATE HELPERS
# -----------------------------------------------------------------------------

class _SkeletonTransformer(ast.NodeTransformer):
    """
    AST Transformer that strips bodies and non-definition nodes.

    Preserves:
    - Function/Class names, decorators, arguments and annotations.
    - Docstrings (as the only body content).
    - Removes: Imports, Assignments, and logic outside definitions.
    """

    def visit_Module(self, node: ast.Module) -> ast.AST:
        """Filter module body to keep only definitions."""
        node.body = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        """Filter class body to keep only methods and nested classes."""
        # We keep Docstrings (ast.Expr) and definitions
        node.body = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Expr))
        ]
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        """Process synchronous and asynchronous function definitions."""
        # 1. Extract docstring if it exists
        docstring = ast.get_docstring(node)

        # 2. Reconstruct the body
        new_body: List[ast.stmt] = []

        if docstring:
            new_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # 3. Add the 'pass' statement to replace logic
        new_body.append(ast.Pass())

        # 4. Update node and return
        node.body = new_body
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        """Handle async definitions identically."""
        return self.visit_FunctionDef(node)