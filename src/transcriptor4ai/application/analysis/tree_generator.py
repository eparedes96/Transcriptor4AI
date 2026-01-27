from __future__ import annotations

"""
Directory Tree Generator Service.

Orchestrates the construction of hierarchical project maps. It integrates 
filesystem traversal with polyglot filtering rules and AST symbol extraction 
to provide a high-level architectural overview suitable for LLM context.
"""

import logging
import os
import re
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from transcriptor4ai.application.analysis.tree_renderer import render_tree_structure
from transcriptor4ai.application.pipeline.components.file_filters import (
    compile_patterns,
    default_exclude_patterns,
    default_extensions,
    default_include_patterns,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)
from transcriptor4ai.domain.entities.file_node import FileNode, Tree
from transcriptor4ai.domain import IFileSystem

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API
# ==============================================================================

def generate_directory_tree(
        fs: IFileSystem,
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
    Generate a formatted visual representation of the project structure.

    This function coordinates the discovery, filtering, and pruning process,
    integrating AST metadata into the leaf nodes when requested.

    Args:
        input_path: Root directory to begin the scan.
        mode: Operation mode ('all', 'modules_only', 'tests_only').
        extensions: Allowed file extensions (e.g., ['.py', '.js']).
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        respect_gitignore: Whether to ingest local .gitignore rules.
        show_functions: Enable AST extraction for functions.
        show_classes: Enable AST extraction for classes.
        show_methods: Enable AST extraction for methods.
        print_to_log: If True, outputs the tree to the logging INFO stream.
        save_path: Optional filesystem path to persist the tree text.

    Returns:
        List[str]: Visual lines of the generated directory tree.
    """
    logger.info(f"TreeGenerator: Initiating scan for {input_path}")

    # 1. SETUP: Compile regex filters from multiple sources
    include_rx, exclude_rx = _setup_tree_filters(
        input_path, extensions, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. SCAN: Build the recursive dictionary-based model
    tree_structure = _build_structure(
        os.path.abspath(input_path),
        mode=mode,
        extensions=extensions or default_extensions(),
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=is_test,
    )

    # 3. OPTIMIZE: Remove empty branches that contain no processed files
    _prune_empty_nodes(tree_structure)

    # 4. RENDER: Transform model into ASCII-art lines
    lines: List[str] = []
    render_tree_structure(
        tree_structure,
        lines,
        prefix="",
        show_functions=show_functions,
        show_classes=show_classes,
        show_methods=show_methods,
    )

    # 5. OUTPUT: Persistence and preview
    if print_to_log:
        logger.info("TreeGenerator: Previewing results:\n" + "\n".join(lines))

    if save_path:
        # 5.1 PERSISTENCE: Delegar la escritura física al puerto de sistema
        content = "\n".join(lines) + "\n"
        fs.write_text_file(save_path, content)
        logger.info(f"TreeGenerator: Persistence delegated to FileSystem for {save_path}")

    return lines


# ==============================================================================
# INTERNAL FILTRATION LOGIC
# ==============================================================================

def _setup_tree_filters(
        path: str,
        exts: Optional[List[str]],
        inc: Optional[List[str]],
        exc: Optional[List[str]],
        gitignore: bool,
) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """Aggregate, sanitize, and compile all filtering patterns into regexes."""

    # 1. EXCLUSIONS: Merge user patterns with system defaults
    final_exclusions = list(exc) if exc is not None else default_exclude_patterns()

    if gitignore:
        git_patterns = load_gitignore_patterns(os.path.abspath(path))
        final_exclusions.extend(git_patterns)

    # 2. INCLUSIONS: Use defaults if no custom rules provided
    final_inclusions = inc or default_include_patterns()

    return compile_patterns(final_inclusions), compile_patterns(final_exclusions)


# ==============================================================================
# SCANNING AND PRUNING ENGINE
# ==============================================================================

def _build_structure(
        input_path: str,
        mode: str,
        extensions: List[str],
        include_patterns_rx: List[re.Pattern],
        exclude_patterns_rx: List[re.Pattern],
        test_detect_func: Callable[[str], bool],
) -> Tree:
    """
    Execute an optimized filesystem walk to construct the recursive Tree model.
    """
    tree_structure: Tree = {}

    for root, dirs, files in os.walk(input_path):
        # 1. FILTER: Prune directories in-place to optimize traversal
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_patterns_rx)]
        dirs.sort()
        files.sort()

        # 2. RESOLVE: Calculate relative depth to build nested dict structure
        rel_root = os.path.relpath(root, input_path)
        if rel_root == ".":
            rel_root = ""

        current_node_level: Tree = tree_structure

        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in current_node_level or not isinstance(current_node_level[p], dict):
                    current_node_level[p] = {}

                # We know it's a dict because we just ensured it
                current_node_level = current_node_level[p]  # type: ignore

        # 3. LEAF PROCESSING: Validate and add files to the current level
        for file_name in files:
            # Check exclusions and inclusions
            if matches_any(file_name, exclude_patterns_rx):
                continue
            if not matches_include(file_name, include_patterns_rx):
                continue

            # Extension check
            _, ext = os.path.splitext(file_name)
            if ext not in extensions:
                continue

            # Target mode classification (Logic vs Tests)
            file_is_test = test_detect_func(file_name)
            if mode == "tests_only" and not file_is_test:
                continue
            if mode == "modules_only" and file_is_test:
                continue

            # Final assignment
            full_path = os.path.join(root, file_name)
            current_node_level[file_name] = FileNode(path=full_path)

    return tree_structure


def _prune_empty_nodes(tree: Tree) -> None:
    """
    Recursively remove directory nodes that contain no valid leaf entries.
    """
    keys_to_remove = []

    for key, value in tree.items():
        if isinstance(value, dict):
            # Recursively prune child directories first
            _prune_empty_nodes(value)

            # Identify if directory became empty after child pruning
            if not value:
                keys_to_remove.append(key)

    # Atomic removal of identified nodes
    for key in keys_to_remove:
        del tree[key]