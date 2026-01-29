from __future__ import annotations

"""
AST Analysis and Transformation Service.

Provides fault-tolerant parsing of Python source files to extract structural 
definitions and generate code skeletons. Supports 'Skeleton Mode' by stripping 
function bodies while preserving signatures, decorators, and docstrings 
to optimize LLM context density.
"""

import ast
import logging
from pathlib import Path
from typing import List

# Standard logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API: SYMBOL EXTRACTION
# ==============================================================================

def extract_definitions(
        file_path: str | Path,
        show_functions: bool,
        show_classes: bool,
        show_methods: bool = False,
) -> List[str]:
    """
    Parse a Python file using AST to extract top-level and nested definitions.

    Handles I/O and syntax errors gracefully to prevent pipeline interruption,
    returning error descriptors instead of raising exceptions.

    Args:
        file_path: Absolute path to the source file to analyze.
        show_functions: Include top-level functions in result.
        show_classes: Include class definitions in result.
        show_methods: Include methods inside classes.

    Returns:
        List[str]: Formatted descriptors of the symbols found.
    """
    results: List[str] = []
    path_obj = Path(file_path)

    # 1. READ: Load file content with encoding resilience
    try:
        source = path_obj.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError) as e:
        msg = f"[ERROR] Could not read '{path_obj.name}': {e}"
        logger.debug(msg)
        return [msg]

    # 2. PARSE: Transform source into Abstract Syntax Tree
    try:
        tree = ast.parse(source, filename=str(path_obj))
    except SyntaxError as e:
        msg = f"[ERROR] Invalid AST (SyntaxError): {e.msg} (line {e.lineno})"
        logger.debug(f"Syntax error in {path_obj}: {e}")
        return [msg]
    except Exception as e:
        msg = f"[ERROR] AST Parsing failed: {e}"
        logger.warning(f"Unexpected AST error in {path_obj}: {e}")
        return [msg]

    # 3. TRAVERSE: Extract symbols based on configuration flags
    for node in tree.body:
        # Process global functions (Sync and Async)
        if show_functions and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            results.append(f"Function: {node.name}()")

        # Process class definitions and their internal methods
        if show_classes and isinstance(node, ast.ClassDef):
            results.append(f"Class: {node.name}")

            if show_methods:
                # Filter internal body for function definitions only (Sync and Async)
                methods = [
                    n.name for n in node.body
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                ]
                for m in methods:
                    results.append(f"  Method: {m}()")

    return results


# ==============================================================================
# PUBLIC API: SKELETON GENERATION
# ==============================================================================

def generate_skeleton_code(source: str) -> str:
    """
    Transform Python source code into a structural skeleton.

    Replaces bodies of functions and methods with 'pass', preserving
    signatures and docstrings. This significantly reduces token usage
    for LLM ingestion without losing architectural context.

    Args:
        source: The original Python source code string.

    Returns:
        str: Skeletonized source code or diagnostic message on failure.
    """
    if not source.strip():
        return ""

    try:
        # 1. PREPARE: Generate initial tree
        tree = ast.parse(source)

        # 2. TRANSFORM: Apply body stripping via NodeTransformer
        transformer = _SkeletonTransformer()
        skeleton_tree = transformer.visit(tree)

        # 3. FINALIZE: Reconstruct source from transformed tree
        # Force location fixing to ensure valid line/col data for unparse
        ast.fix_missing_locations(skeleton_tree)
        return ast.unparse(skeleton_tree)

    except SyntaxError as e:
        logger.warning(f"Skeletonization failed (SyntaxError): {e}")
        return f"# [SKIPPING SKELETON] File has SyntaxError: {e}\n"
    except Exception as e:
        logger.error(f"Unexpected error during skeletonization: {e}")
        return f"# [ERROR] AST skeletonization failed: {str(e)}\n"


# ==============================================================================
# PRIVATE HELPERS: AST TRANSFORMERS
# ==============================================================================

class _SkeletonTransformer(ast.NodeTransformer):
    """
    AST Transformer that strips implementation logic while preserving structure.

    Preserves:
    - Definitions (Class, Function, AsyncFunction).
    - Signatures (Arguments, Decorators, Annotations).
    - Documentation (Docstrings).

    Removes:
    - Logical bodies (replaced by 'pass').
    - Assignments and logic outside definitions.
    - Imports (to keep focus on local logic).
    """

    def visit_Module(self, node: ast.Module) -> ast.AST:
        """Keep only definitions at module level."""
        node.body = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        return self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.AST:
        """Keep only methods, nested classes, and docstrings."""
        # Docstrings are ast.Expr containing an ast.Constant/Str at the start of body
        node.body = [
            n for n in node.body
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Expr))
        ]
        return self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> ast.AST:
        """Strip logic and replace with 'pass', preserving docstring."""
        # 1. ANALYZE: Retrieve existing docstring
        docstring = ast.get_docstring(node)

        # 2. RECONSTRUCT: Create minimal body
        new_body: List[ast.stmt] = []

        if docstring:
            # Re-inject docstring as an Expression node
            new_body.append(ast.Expr(value=ast.Constant(value=docstring)))

        # Append 'pass' to maintain valid Python syntax
        new_body.append(ast.Pass())

        # 3. APPLY: Override node body
        node.body = new_body
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        """Handle async definitions with identical logic to synchronous ones."""
        return self.visit_FunctionDef(node)