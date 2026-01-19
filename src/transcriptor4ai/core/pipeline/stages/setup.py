from __future__ import annotations

"""
Pipeline Setup & Environment Preparation Stage.

Handles the initialization lifecycle of the pipeline:
1. Path normalization and filesystem validation.
2. Conflict detection for pre-existing output files.
3. Staging area creation (Temporary vs. Final directories).
4. Context mapping for downstream stages.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.domain.pipeline_models import PipelineResult, create_error_result
from transcriptor4ai.infra.fs import (
    check_existing_output_files,
    get_real_output_path,
    normalize_path,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# ENVIRONMENT PREPARATION LOGIC
# ==============================================================================

def prepare_environment(
        cfg: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        tree_output_path: Optional[str]
) -> Tuple[Optional[PipelineResult], Dict[str, Any]]:
    """
    Initialize the filesystem state and execution context for the pipeline.

    Calculates absolute paths for all potential outputs, checks for naming
    collisions, and establishes the staging area for transcription workers.

    Args:
        cfg: Validated configuration dictionary.
        overwrite: Whether to allow overwriting of existing files.
        dry_run: Whether execution is a simulation.
        tree_output_path: Optional override for the directory tree file path.

    Returns:
        Tuple[Optional[PipelineResult], Dict[str, Any]]:
            A PipelineResult object if setup fails, else None and the
            environment context dictionary.
    """
    # --- 1. Path Normalization and Validation ---
    fallback_base = os.getcwd()
    base_path = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid or non-existent input directory: {base_path}"
        logger.error(msg)
        return create_error_result(msg, cfg, base_path), {}

    # Resolve output directory hierarchy
    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), base_path)
    final_output_path = get_real_output_path(output_base_dir, cfg["output_subdir_name"])
    prefix = cfg["output_prefix"]

    # --- 2. Collision Detection (Overwrite Check) ---
    files_to_check: List[str] = []

    # Map possible files based on configuration flags
    if cfg["create_individual_files"]:
        if cfg["process_modules"]:
            files_to_check.append(f"{prefix}_modules.txt")
        if cfg["process_tests"]:
            files_to_check.append(f"{prefix}_tests.txt")
        if cfg["process_resources"]:
            files_to_check.append(f"{prefix}_resources.txt")
        if cfg["generate_tree"]:
            files_to_check.append(f"{prefix}_tree.txt")

    if cfg["create_unified_file"]:
        files_to_check.append(f"{prefix}_full_context.txt")

    if cfg["save_error_log"]:
        files_to_check.append(f"{prefix}_errors.txt")

    # Verify physical existence in target directory
    existing_files = check_existing_output_files(final_output_path, files_to_check)

    if existing_files and not overwrite and not dry_run:
        msg = "Naming collision detected: Output files already exist and overwrite is disabled."
        logger.warning(f"{msg} Target files: {existing_files}")
        return create_error_result(
            msg, cfg, base_path, final_output_path, existing_files,
            summary_extra={"existing_files": list(existing_files)}
        ), {}

    # --- 3. Directory and Staging Initialization ---
    if not dry_run:
        try:
            os.makedirs(final_output_path, exist_ok=True)
        except OSError as e:
            msg = f"Critical error creating output directory {final_output_path}: {e}"
            logger.critical(msg)
            return create_error_result(msg, cfg, base_path, final_output_path), {}

    # Setup staging area: uses TemporaryDirectory if simulation or unified-only mode
    temp_dir_obj = None
    if dry_run or not cfg["create_individual_files"]:
        temp_dir_obj = tempfile.TemporaryDirectory()
        staging_dir = temp_dir_obj.name
        logger.debug(f"Staging area initialized in temporary directory: {staging_dir}")
    else:
        staging_dir = final_output_path

    # Define intermediate file paths (Fixed E501 by breaking long join)
    tree_path = tree_output_path
    if not tree_path:
        tree_path = os.path.join(staging_dir, f"{prefix}_tree.txt")

    paths = {
        "modules": os.path.join(staging_dir, f"{prefix}_modules.txt"),
        "tests": os.path.join(staging_dir, f"{prefix}_tests.txt"),
        "resources": os.path.join(staging_dir, f"{prefix}_resources.txt"),
        "tree": tree_path,
        "errors": os.path.join(staging_dir, f"{prefix}_errors.txt"),
        "unified": os.path.join(staging_dir, f"{prefix}_full_context.txt"),
    }

    # Bundle environment state for worker orchestration
    env_context = {
        "base_path": base_path,
        "final_output_path": final_output_path,
        "staging_dir": staging_dir,
        "temp_dir_obj": temp_dir_obj,
        "prefix": prefix,
        "paths": paths,
        "existing_files": existing_files,
        "files_to_check": files_to_check
    }

    logger.info("Pipeline environment setup complete.")
    return None, env_context