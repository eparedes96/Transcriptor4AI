from __future__ import annotations

"""
Directory Tree Generator.

Constructs a hierarchical representation of project structures. Integrates 
with the filtering system and AST service to provide high-level context 
while respecting exclusion rules and .gitignore patterns.
"""

import logging
import os
import re
from typing import Callable, List, Optional, Tuple

from transcriptor4ai.core.analysis.tree_renderer import render_tree_structure
from transcriptor4ai.core.pipeline.components.filters import (
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

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

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
    Generate a formatted text representation of the directory structure.

    Orchestrates the scanning, filtering, and rendering of the tree.
    Supports pruning of empty branches after filtering.

    Args:
        input_path: Source directory for the scan.
        mode: Filtering mode (all/modules/tests).
        extensions: Allowed file extensions.
        include_patterns: Inclusion regexes.
        exclude_patterns: Exclusion regexes.
        respect_gitignore: Flag to enable .gitignore parsing.
        show_functions: Flag to enable AST function extraction.
        show_classes: Flag to enable AST class extraction.
        show_methods: Flag to enable AST method extraction.
        print_to_log: Whether to log the output to INFO.
        save_path: Optional file path to persist the tree.

    Returns:
        List[str]: Visual lines of the generated tree.
    """
    logger.info(f"Generating directory tree for: {input_path}")

    # 1. Compile and aggregate filtering rules
    include_rx, exclude_rx = _setup_tree_filters(
        input_path, extensions, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. Build recursive dictionary structure and prune empty branches
    tree_structure = _build_structure(
        os.path.abspath(input_path),
        mode=mode,
        extensions=extensions or default_extensions(),
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=is_test,
    )
    _prune_empty_nodes(tree_structure)

    # 3. Rendering and persistence
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

# -----------------------------------------------------------------------------
# INTERNAL HELPERS (FILTERS AND STORAGE)
# -----------------------------------------------------------------------------

def _setup_tree_filters(
        path: str,
        exts: Optional[List[str]],
        inc: Optional[List[str]],
        exc: Optional[List[str]],
        gitignore: bool
) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """Aggregate and compile all filtering patterns into regex objects."""
    final_exclusions = list(exc) if exc is not None else default_exclude_patterns()
    if gitignore:
        git_patterns = load_gitignore_patterns(os.path.abspath(path))
        final_exclusions.extend(git_patterns)

    return compile_patterns(inc or default_include_patterns()), compile_patterns(final_exclusions)


def _save_tree_to_disk(save_path: str, lines: List[str]) -> None:
    """Safely persist tree lines to the filesystem."""
    try:
        out_dir = os.path.dirname(os.path.abspath(save_path))
        os.makedirs(out_dir, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        logger.info(f"Tree saved to file: {save_path}")
    except OSError as e:
        logger.error(f"Failed to save tree to '{save_path}': {e}")

# -----------------------------------------------------------------------------
# INTERNAL HELPERS (SCANNING AND PRUNING)
# -----------------------------------------------------------------------------

def _build_structure(
        input_path: str,
        mode: str,
        extensions: List[str],
        include_patterns_rx: List[re.Pattern],
        exclude_patterns_rx: List[re.Pattern],
        test_detect_func: Callable[[str], bool],
) -> Tree:
    """
    Execute filesystem walk to build the recursive Tree model.
    """
    tree_structure: Tree = {}

    # In-place modification of dirs for recursive pruning during walk
    for root, dirs, files in os.walk(input_path):
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_patterns_rx)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, input_path)
        if rel_root == ".":
            rel_root = ""

        # Tree navigation and level creation
        current_node_level: Tree = tree_structure
        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in current_node_level or not isinstance(current_node_level[p], dict):
                    current_node_level[p] = {}
                next_level = current_node_level[p]
                if isinstance(next_level, dict):
                    current_node_level = next_level

        # Leaf processing (Files)
        for file_name in files:
            if matches_any(file_name, exclude_patterns_rx):
                continue
            if not matches_include(file_name, include_patterns_rx):
                continue
            _, ext = os.path.splitext(file_name)
            if ext not in extensions:
                continue

            # Core filtering logic based on processing mode
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
    Recursively remove empty directory nodes from the Tree model.
    """
    keys_to_remove = []

    for key, value in tree.items():
        if isinstance(value, dict):
            _prune_empty_nodes(value)
            if not value:
                keys_to_remove.append(key)

    for key in keys_to_remove:
        del tree[key]