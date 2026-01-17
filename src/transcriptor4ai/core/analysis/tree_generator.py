from __future__ import annotations

"""
Directory Tree Generator.

Builds a hierarchical representation of the project structure.
Supports filtering, Gitignore rules, and AST symbol integration.
"""

import logging
import os
import re
from typing import Callable, List, Optional, Tuple

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

    # 1. Preparar filtros y reglas
    include_rx, exclude_rx = _setup_tree_filters(
        input_path, extensions, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. Construir y podar estructura
    tree_structure = _build_structure(
        os.path.abspath(input_path),
        mode=mode,
        extensions=extensions or default_extensions(),
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=is_test,
    )
    _prune_empty_nodes(tree_structure)

    # 3. Renderizado y salida
    lines: List[str] = []
    render_tree_structure(
        tree_structure, lines, prefix="",
        show_functions=show_functions, show_classes=show_classes, show_methods=show_methods
    )

    if print_to_log:
        logger.info("Tree Preview:\n" + "\n".join(lines))

    if save_path:
        _save_tree_to_disk(save_path, lines)

    return lines


def _setup_tree_filters(
        path: str,
        exts: Optional[List[str]],
        inc: Optional[List[str]],
        exc: Optional[List[str]],
        gitignore: bool
) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """Internal helper to consolidate regex patterns for the tree scanner."""
    final_exclusions = list(exc) if exc is not None else default_exclude_patterns()
    if gitignore:
        git_patterns = load_gitignore_patterns(os.path.abspath(path))
        final_exclusions.extend(git_patterns)

    return compile_patterns(inc or default_include_patterns()), compile_patterns(final_exclusions)


def _save_tree_to_disk(save_path: str, lines: List[str]) -> None:
    """Internal helper to handle safe file writing of the tree."""
    try:
        out_dir = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(out_dir, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Tree saved to file: {save_path}")
    except OSError as e:
        logger.error(f"Failed to save tree to '{save_path}': {e}")


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