from __future__ import annotations

"""
Pipeline-Specific Filesystem Workflow Service.

Orchestrates complex I/O operations required for the transcription lifecycle,
including staging path construction, artifact aggregation (Master Context),
and atomic deployment to final user directories.
"""

import logging
import os
import shutil
from typing import Dict, Optional

from transcriptor4ai.infrastructure.system.fs.io_manager import move_file

# Local module logger
logger = logging.getLogger(__name__)


# ==============================================================================
# STAGING CONFIGURATION
# ==============================================================================

def build_staging_paths(
        staging_dir: str,
        prefix: str,
        tree_override: Optional[str] = None
) -> Dict[str, str]:
    """
    Construct absolute filesystem paths for all pipeline staging artifacts.

    Args:
        staging_dir: Directory where temporary files are generated.
        prefix: User-defined filename prefix.
        tree_override: Optional explicit path for the directory tree.

    Returns:
        Dict[str, str]: Map of category identifiers to absolute file paths.
    """
    return {
        "modules": os.path.join(staging_dir, f"{prefix}_modules.txt"),
        "tests": os.path.join(staging_dir, f"{prefix}_tests.txt"),
        "resources": os.path.join(staging_dir, f"{prefix}_resources.txt"),
        "tree": tree_override or os.path.join(staging_dir, f"{prefix}_tree.txt"),
        "errors": os.path.join(staging_dir, f"{prefix}_errors.txt"),
        "unified": os.path.join(staging_dir, f"{prefix}_full_context.txt"),
    }


# ==============================================================================
# ARTIFACT AGGREGATION
# ==============================================================================

def generate_unified_file(
        output_path: str,
        base_path: str,
        tree_path: Optional[str],
        category_paths: Dict[str, str]
) -> bool:
    """
    Stream and aggregate multiple artifacts into a single LLM-optimized context file.

    Args:
        output_path: Destination for the unified Master Context.
        base_path: Source project path (used for the header).
        tree_path: Path to the generated directory structure file.
        category_paths: Map of successfully generated categorized files.

    Returns:
        bool: True if aggregation succeeded, False on I/O error.
    """
    try:
        with open(output_path, "w", encoding="utf-8") as outfile:
            # 1. HEADER: Define project identity for LLM parsing
            base_name = os.path.basename(base_path)
            outfile.write(f"PROJECT CONTEXT: {base_name}\n" + "=" * 80 + "\n\n")

            # 2. STRUCTURE: Append directory tree if available
            if tree_path and os.path.exists(tree_path):
                outfile.write("PROJECT STRUCTURE:\n" + "-" * 50 + "\n")
                with open(tree_path, "r", encoding="utf-8") as infile:
                    shutil.copyfileobj(infile, outfile)  # Efficient stream copy
                outfile.write("\n\n")

            # 3. CONTENT: Aggregate code and resource blocks
            for key in ["modules", "tests", "resources"]:
                path = category_paths.get(key)
                if path and os.path.exists(path):
                    with open(path, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")
        return True

    except OSError as e:
        logger.error(f"PipelineIO: Master Context aggregation failed: {e}")
        return False


# ==============================================================================
# DEPLOYMENT COORDINATION
# ==============================================================================

def deploy_pipeline_artifacts(
        staging_paths: Dict[str, str],
        final_dir: str,
        prefix: str,
        unified_ok: bool,
        results_map: Dict[str, str]
) -> None:
    """
    Finalize the execution by moving files from staging to their final destination.

    Handles path collisions by checking absolute path equality to prevent
    deleting data when staging_dir == final_dir.

    Args:
        staging_paths: Map of files currently in the staging area.
        final_dir: User-defined destination directory.
        prefix: Filename prefix.
        unified_ok: Flag indicating if the Master Context was created.
        results_map: Output map updated with final physical paths.
    """
    # 1. UNIFIED CONTEXT DEPLOYMENT
    if unified_ok:
        dest_unified = os.path.join(final_dir, f"{prefix}_full_context.txt")
        src_unified = staging_paths["unified"]

        # Only move if paths are different (prevents deletion on same-folder runs)
        if os.path.abspath(src_unified) != os.path.abspath(dest_unified):
            if move_file(src_unified, dest_unified):
                results_map["unified"] = dest_unified
        else:
            results_map["unified"] = dest_unified

    # 2. ERROR LOG DEPLOYMENT
    err_staging = staging_paths.get("errors")
    if err_staging and os.path.exists(err_staging):
        dest_errors = os.path.join(final_dir, f"{prefix}_errors.txt")

        if os.path.abspath(err_staging) != os.path.abspath(dest_errors):
            move_file(err_staging, dest_errors)