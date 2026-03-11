from __future__ import annotations

"""
Directory Tree Generation Service.

Orchestrates the construction of hierarchical project maps by integrating 
filesystem traversal with polyglot filtering rules and AST symbol extraction. 
Produces high-level architectural overviews optimized for LLM context density.
"""

import logging
import os
import re
from typing import Callable, List, Optional, Tuple

# Internal Analysis & Rendering
from transcriptor4ai.application.analysis.tree_renderer import render_tree_structure
from transcriptor4ai.application.common.file_filters import (
    compile_patterns,
    default_exclude_patterns,
    default_extensions,
    default_include_patterns,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)

# Domain Entities & Ports
from transcriptor4ai.domain.entities.file_node import FileNode, Tree
from transcriptor4ai.domain.ports.system_port import IFileSystem

# Standardized logger for the analysis domain
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API: TREE GENERATION
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

    Args:
        fs: Abstracted file system implementation for persistence.
        input_path: Root directory to begin the recursive scan.
        mode: Operation mode ('all', 'modules_only', 'tests_only').
        extensions: Allowed file extensions (e.g., ['.py', '.js']).
        include_patterns: Regex whitelist patterns for files.
        exclude_patterns: Regex blacklist patterns for files/dirs.
        respect_gitignore: If True, ingests local .gitignore rules.
        show_functions: Enable AST extraction for function signatures.
        show_classes: Enable AST extraction for class definitions.
        show_methods: Enable AST extraction for nested methods.
        print_to_log: If True, outputs the tree to the INFO log stream.
        save_path: Optional destination for the generated ASCII file.

    Returns:
        List[str]: Formatted ASCII lines of the project structure.
    """
    logger.info(f"TreeGenerator: Initiating architectural scan for {input_path}")

    # 1. SETUP: Aggregate and compile filtering rules from all sources
    include_rx, exclude_rx = _setup_tree_filters(
        input_path, extensions, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. SCAN: Traverse filesystem and build the recursive dictionary model
    tree_structure = _build_structure(
        os.path.abspath(input_path),
        mode=mode,
        extensions=extensions or default_extensions(),
        include_patterns_rx=include_rx,
        exclude_patterns_rx=exclude_rx,
        test_detect_func=is_test,
    )

    # 3. OPTIMIZE: Recursively remove directory nodes with no valid leaves
    _prune_empty_nodes(tree_structure)

    # 4. RENDER: Transform the internal model into a list of ASCII strings
    lines: List[str] = []
    render_tree_structure(
        tree_structure,
        lines,
        prefix="",
        show_functions=show_functions,
        show_classes=show_classes,
        show_methods=show_methods,
    )

    # 5. OUTPUT: Handle logging and delegated persistence
    if print_to_log:
        logger.info("TreeGenerator: Previewing results:\n" + "\n".join(lines))

    if save_path:
        # Persistence is delegated to the FileSystem port for architectural purity
        content = "\n".join(lines) + "\n"
        fs.write_text_file(save_path, content)
        logger.info(f"TreeGenerator: Tree successfully persisted to {save_path}")

    return lines


# ==============================================================================
# INTERNAL LOGIC: FILTRATION & DISCOVERY
# ==============================================================================

def _setup_tree_filters(
        path: str,
        exts: Optional[List[str]],
        inc: Optional[List[str]],
        exc: Optional[List[str]],
        gitignore: bool,
) -> Tuple[List[re.Pattern], List[re.Pattern]]:
    """Aggregate, sanitize, and compile all filtering patterns into regexes."""

    # 1. EXCLUSIONS: Merge user patterns with system-level noise defaults
    final_exclusions = list(exc) if exc is not None else default_exclude_patterns()

    if gitignore:
        git_patterns = load_gitignore_patterns(os.path.abspath(path))
        final_exclusions.extend(git_patterns)

    # 2. INCLUSIONS: Define strict whitelist (defaults to matching everything)
    final_inclusions = inc or default_include_patterns()

    return compile_patterns(final_inclusions), compile_patterns(final_exclusions)


def _build_structure(
        input_path: str,
        mode: str,
        extensions: List[str],
        include_patterns_rx: List[re.Pattern],
        exclude_patterns_rx: List[re.Pattern],
        test_detect_func: Callable[[str], bool],
) -> Tree:
    """
    Execute an optimized walk to construct the internal Tree data model.
    """
    tree_structure: Tree = {}

    for root, dirs, files in os.walk(input_path):
        # 1. PRUNING: Modify dirs in-place to prevent entering excluded branches
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_patterns_rx)]
        dirs.sort()
        files.sort()

        # 2. RESOLUTION: Calculate hierarchy level relative to input root
        rel_root = os.path.relpath(root, input_path)
        if rel_root == ".":
            rel_root = ""

        current_node_level: Tree = tree_structure

        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in current_node_level or not isinstance(current_node_level[p], dict):
                    current_node_level[p] = {}

                # Traverse deeper into the structure
                current_node_level = current_node_level[p]  # type: ignore

        # 3. LEAF PROCESSING: Validate files against polyglot and mode rules
        for file_name in files:
            # Apply regex and extension filters
            if matches_any(file_name, exclude_patterns_rx):
                continue
            if not matches_include(file_name, include_patterns_rx):
                continue

            _, ext = os.path.splitext(file_name)
            if ext not in extensions:
                continue

            # Apply domain processing mode (Modules vs Tests only)
            file_is_test = test_detect_func(file_name)
            if mode == "tests_only" and not file_is_test:
                continue
            if mode == "modules_only" and file_is_test:
                continue

            # Construct immutable leaf node
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
            # 1. DEPTH-FIRST: Recurse into child branches first
            _prune_empty_nodes(value)

            # 2. EVALUATION: Mark node for removal if empty after recursion
            if not value:
                keys_to_remove.append(key)

    # 3. CLEANUP: Physically remove identified nodes
    for key in keys_to_remove:
        del tree[key]