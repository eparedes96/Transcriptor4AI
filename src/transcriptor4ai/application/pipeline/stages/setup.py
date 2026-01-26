from __future__ import annotations

"""
Pipeline Setup Stage.

Orchestrates the initialization of the execution environment by:
1. Validating input path integrity via the injected FileSystem port.
2. Resolving the output directory hierarchy.
3. Detecting naming collisions via infrastructure-defined artifact schemas.
4. Initializing the staging area (Physical or Temporary) for concurrent workers.
"""

import logging
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

from transcriptor4ai.domain.entities.pipeline_results import PipelineResult, create_error_result
from transcriptor4ai.domain.ports.system_port import IFileSystem

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# STAGE: PIPELINE SETUP
# ==============================================================================

def prepare_environment(
        fs: IFileSystem,
        cfg: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        tree_output_path: Optional[str],
) -> Tuple[Optional[PipelineResult], Dict[str, Any]]:
    """
    Initialize the filesystem state and execution context for the pipeline.

    Calculates absolute paths for all potential outputs, checks for naming
    collisions, and establishes the staging area for transcription workers.

    Args:
        fs: Injected implementation of the FileSystem port.
        cfg: Validated configuration dictionary.
        overwrite: Permission to replace existing files.
        dry_run: Simulation mode flag.
        tree_output_path: Optional override for the tree file location.

    Returns:
        Tuple[Optional[PipelineResult], Dict[str, Any]]:
            Error result if setup fails, otherwise (None, env_context).
    """

    # 1. VALIDATION: Resolve and check input directory integrity
    base_path = fs.normalize_path(cfg.get("input_path", ""), fallback=".")

    # We use os.path here only for state validation; the resolution was handled by the port
    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid or non-existent input directory: {base_path}"
        logger.error(msg)
        return create_error_result(msg, cfg, base_path), {}

    # 2. RESOLUTION: Determine final output destination
    output_base_dir = fs.normalize_path(cfg.get("output_base_dir", ""), fallback=base_path)
    final_output_path = fs.get_real_output_path(output_base_dir, cfg["output_subdir_name"])
    prefix = cfg["output_prefix"]

    # 3. COLLISIONS: Identify potential naming conflicts using adapter schemas
    # Logic for "how files are named" is now encapsulated in the FileSystem adapter
    files_to_check = fs.get_expected_filenames(cfg, prefix)
    existing_files = fs.check_existing_output_files(final_output_path, files_to_check)

    if existing_files and not overwrite and not dry_run:
        msg = "Naming collision detected: Output files already exist and overwrite is disabled."
        logger.warning(f"{msg} Target files: {existing_files}")
        return create_error_result(
            msg, cfg, base_path, final_output_path, existing_files,
            summary_extra={"existing_files": list(existing_files)}
        ), {}

    # 4. INITIALIZATION: Setup directory structure and staging area
    if not dry_run:
        success, err = fs.safe_mkdir(final_output_path)
        if not success:
            msg = f"Critical error creating output directory {final_output_path}: {err}"
            logger.critical(msg)
            return create_error_result(msg, cfg, base_path, final_output_path), {}

    # Selection of staging area: uses TemporaryDirectory for dry runs or restricted runs
    temp_dir_obj = None
    if dry_run or not cfg["create_individual_files"]:
        temp_dir_obj = tempfile.TemporaryDirectory()
        staging_dir = temp_dir_obj.name
        logger.debug(f"Setup: Staging area initialized in temp dir: {staging_dir}")
    else:
        staging_dir = final_output_path

    # 5. MAPPING: Construct staging paths via adapter
    paths = fs.build_staging_paths(staging_dir, prefix, tree_output_path)

    # Bundle environment state for worker orchestration and final assembly
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

    logger.info("Pipeline: Environment preparation stage complete.")
    return None, env_context