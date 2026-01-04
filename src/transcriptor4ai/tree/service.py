from __future__ import annotations

"""
Directory tree generation service.

Builds a hierarchical representation of the project structure and 
extracts AST symbols if configured.
"""

import logging
import os
import re
from typing import Callable, List, Optional

from transcriptor4ai.filtering import (
    compile_patterns,
    default_extensiones,
    default_exclude_patterns,
    default_include_patterns,
    es_test,
    matches_any,
    matches_include,
)
from transcriptor4ai.tree.models import FileNode, Tree
from transcriptor4ai.tree.render import render_tree_structure

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def generate_directory_tree(
        input_path: str,
        mode: str = "todo",
        extensions: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
        print_to_log: bool = False,
        save_path: str = "",
) -> List[str]:
    """
    Generate a hierarchical text representation of the file structure.

    Optionally parses files to show symbols (functions, classes, methods).
    This service does NOT print to stdout.

    Args:
        input_path: Root directory to scan.
        mode: Processing mode ("todo", "solo_modulos", "solo_tests").
        extensions: List of allowed file extensions.
        include_patterns: Regex patterns for inclusion.
        exclude_patterns: Regex patterns for exclusion.
        show_functions: If True, parse and show top-level functions.
        show_classes: If True, parse and show top-level classes.
        show_methods: If True (and classes=True), show methods.
        print_to_log: If True, logs the tree at INFO level.
        save_path: If provided, saves the tree to this file path.

    Returns:
        A list of strings representing the tree lines.
    """
    logger.info(f"Generating directory tree for: {input_path}")

    # -------------------------
    # Input Normalization
    # -------------------------
    if extensions is None:
        extensions = default_extensiones()
    if include_patterns is None:
        include_patterns = default_include_patterns()
    if exclude_patterns is None:
        exclude_patterns = default_exclude_patterns()

    input_path_abs = os.path.abspath(input_path)

    include_rx = compile_patterns(include_patterns)
    exclude_rx = compile_patterns(exclude_patterns)

    # -------------------------
    # Build Structure
    # -------------------------
    tree_structure = _build_structure(
        input_path_abs,
        mode=mode,
        extensions=extensions,
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=es_test,
    )

    # -------------------------
    # Render Tree
    # -------------------------
    lines: List[str] = []
    render_tree_structure(
        tree_structure,
        lines,
        prefix="",
        show_functions=show_functions,
        show_classes=show_classes,
        show_methods=show_methods,
    )

    # -------------------------
    # Output Handling
    # -------------------------
    if print_to_log:
        logger.info("Tree Preview:\n" + "\n".join(lines))

    if save_path:
        try:
            out_dir = os.path.dirname(os.path.abspath(save_path))
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            with open(save_path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

            logger.info(f"Tree saved to file: {save_path}")
        except OSError as e:
            msg = f"Failed to save tree to '{save_path}': {e}"
            logger.error(msg)
            lines.append(f"[ERROR] {msg}")

    return lines


# -----------------------------------------------------------------------------
# Internal Helpers
# -----------------------------------------------------------------------------
def _build_structure(
        input_path: str,
        mode: str,
        extensions: List[str],
        include_patterns_rx: List[re.Pattern],
        exclude_patterns_rx: List[re.Pattern],
        test_detect_func: Callable[[str], bool],
) -> Tree:
    """Recursively build the Tree dictionary from the filesystem."""
    tree_structure: Tree = {}

    for root, dirs, files in os.walk(input_path):
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_patterns_rx)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, input_path)
        if rel_root == ".":
            rel_root = ""

        # Navigate or create intermediate nodes
        current_node_level: Tree = tree_structure
        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in current_node_level or not isinstance(current_node_level[p], dict):
                    current_node_level[p] = {}
                next_level = current_node_level[p]
                if isinstance(next_level, dict):
                    current_node_level = next_level

        # Process Files
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext not in extensions:
                continue

            # Check Patterns
            if matches_any(file_name, exclude_patterns_rx):
                continue
            if not matches_include(file_name, include_patterns_rx):
                continue

            # Check Mode (Tests/Modules)
            file_is_test = test_detect_func(file_name)
            if mode == "solo_tests" and not file_is_test:
                continue
            if mode == "solo_modulos" and file_is_test:
                continue

            # Add File Node
            full_path = os.path.join(root, file_name)
            current_node_level[file_name] = FileNode(path=full_path)

    return tree_structure