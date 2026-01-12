from __future__ import annotations

"""
Directory Tree Generator.

Builds a hierarchical representation of the project structure.
Supports filtering, Gitignore rules, and AST symbol integration.
"""

import logging
import os
import re
from typing import Callable, List, Optional

from transcriptor4ai.core.analysis.tree_renderer import render_tree_structure
from transcriptor4ai.core.pipeline.filters import (
    compile_patterns,
    default_extensions,
    default_exclude_patterns,
    default_include_patterns,
    load_gitignore_patterns,
    is_test,
    matches_any,
    matches_include,
)
from transcriptor4ai.domain.tree_models import FileNode, Tree

logger = logging.getLogger(__name__)


def generate_directory_tree(
        input_path: str,
        mode: str = "all",
        extensions: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        respect_gitignore: bool = True,
        show_functions: bool = False,
        show_classes: bool = False,
        show_methods: bool = False,
        print_to_log: bool = False,
        save_path: str = "",
) -> List[str]:
    """
    Generate a text-based tree representation of the directory structure.

    Args:
        input_path: Root directory to scan.
        mode: Scan mode ("all", "modules_only", "tests_only").
        extensions: List of allowed file extensions.
        include_patterns: Regex patterns for inclusion.
        exclude_patterns: Regex patterns for exclusion.
        respect_gitignore: Whether to parse .gitignore files.
        show_functions: Whether to list functions (Python only).
        show_classes: Whether to list classes (Python only).
        show_methods: Whether to list methods (Python only).
        print_to_log: If True, log the tree to INFO.
        save_path: If provided, save the tree to this file.

    Returns:
        List[str]: The lines of the generated tree.
    """
    logger.info(f"Generating directory tree for: {input_path}")

    # 1. Normalization
    if extensions is None:
        extensions = default_extensions()
    if include_patterns is None:
        include_patterns = default_include_patterns()
    if exclude_patterns is None:
        exclude_patterns = default_exclude_patterns()

    input_path_abs = os.path.abspath(input_path)

    # 2. Pattern Compilation
    final_exclusions = list(exclude_patterns)
    if respect_gitignore:
        git_patterns = load_gitignore_patterns(input_path_abs)
        if git_patterns:
            logger.debug(f"Tree generator loaded {len(git_patterns)} patterns from .gitignore")
            final_exclusions.extend(git_patterns)

    include_rx = compile_patterns(include_patterns)
    exclude_rx = compile_patterns(final_exclusions)

    # 3. Build Internal Structure
    tree_structure = _build_structure(
        input_path_abs,
        mode=mode,
        extensions=extensions,
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=is_test,
    )

    # 4. Prune Empty Directories
    _prune_empty_nodes(tree_structure)

    # 5. Render to Text
    lines: List[str] = []
    render_tree_structure(
        tree_structure,
        lines,
        prefix="",
        show_functions=show_functions,
        show_classes=show_classes,
        show_methods=show_methods,
    )

    # 6. Output Handling
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


def _build_structure(
        input_path: str,
        mode: str,
        extensions: List[str],
        include_patterns_rx: List[re.Pattern],
        exclude_patterns_rx: List[re.Pattern],
        test_detect_func: Callable[[str], bool],
) -> Tree:
    """
    Recursively scan the filesystem and build a Tree dictionary.
    """
    tree_structure: Tree = {}

    for root, dirs, files in os.walk(input_path):
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_patterns_rx)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, input_path)
        if rel_root == ".":
            rel_root = ""

        # Navigate/Create current node in the structure
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
            if matches_any(file_name, exclude_patterns_rx):
                continue
            if not matches_include(file_name, include_patterns_rx):
                continue
            _, ext = os.path.splitext(file_name)
            if ext not in extensions:
                continue

            # Filtering Mode Logic
            file_is_test = test_detect_func(file_name)
            if mode == "tests_only" and not file_is_test:
                continue
            if mode == "modules_only" and file_is_test:
                continue

            # Add File Node
            full_path = os.path.join(root, file_name)
            current_node_level[file_name] = FileNode(path=full_path)

    return tree_structure


def _prune_empty_nodes(tree: Tree) -> None:
    """
    Recursively remove directory nodes (dicts) that are empty.
    This cleans up the tree if filters removed all files in a folder.

    Args:
        tree: The recursive dictionary structure to clean.
    """
    keys_to_remove = []

    for key, value in tree.items():
        if isinstance(value, dict):
            _prune_empty_nodes(value)
            if not value:
                keys_to_remove.append(key)

    for key in keys_to_remove:
        del tree[key]