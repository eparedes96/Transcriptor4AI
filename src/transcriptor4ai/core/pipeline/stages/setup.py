from __future__ import annotations

"""
Pipeline Setup & Preparation.

This module handles the initialization phase of the pipeline:
1. Path normalization and validation.
2. Conflict detection (existing files).
3. Directory creation (final and staging).
4. Path definitions for intermediate files.
"""

import logging
import os
import tempfile
from typing import Any, Dict, List, Optional, Tuple, Union

from transcriptor4ai.domain.pipeline_models import (
    PipelineResult,
    create_error_result
)
from transcriptor4ai.infra.fs import (
    check_existing_output_files,
    normalize_path,
    get_real_output_path,
)

logger = logging.getLogger(__name__)


def prepare_environment(
        cfg: Dict[str, Any],
        overwrite: bool,
        dry_run: bool,
        tree_output_path: Optional[str]
) -> Tuple[Optional[PipelineResult], Dict[str, Any]]:
    """
    Prepare the filesystem and execution context for the pipeline.

    Args:
        cfg: The validated configuration dictionary.
        overwrite: Whether to overwrite existing files.
        dry_run: Whether to simulate execution.
        tree_output_path: Optional override for tree file path.

    Returns:
        Tuple containing:
        1. PipelineResult (if an error occurred during setup, else None).
        2. Context Dictionary (containing paths, temp objects, and state data).
    """
    fallback_base = os.getcwd()
    base_path = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid input directory: {base_path}"
        logger.error(msg)
        return create_error_result(msg, cfg, base_path), {}

    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), base_path)
    final_output_path = get_real_output_path(output_base_dir, cfg["output_subdir_name"])
    prefix = cfg["output_prefix"]

    # -------------------------------------------------------------------------
    # Overwrite Check
    # -------------------------------------------------------------------------
    files_to_check: List[str] = []

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

    existing_files = check_existing_output_files(final_output_path, files_to_check)

    if existing_files and not overwrite and not dry_run:
        msg = "Existing files detected and overwrite=False. Aborting."
        logger.warning(f"{msg} Files: {existing_files}")
        return create_error_result(
            msg, cfg, base_path, final_output_path, existing_files,
            summary_extra={"existing_files": list(existing_files)}
        ), {}

    # -------------------------------------------------------------------------
    # Directory & Staging Preparation
    # -------------------------------------------------------------------------
    if not dry_run:
        try:
            os.makedirs(final_output_path, exist_ok=True)
        except OSError as e:
            msg = f"Failed to create output directory {final_output_path}: {e}"
            logger.critical(msg)
            return create_error_result(msg, cfg, base_path, final_output_path), {}

    temp_dir_obj = None
    if dry_run or not cfg["create_individual_files"]:
        temp_dir_obj = tempfile.TemporaryDirectory()
        staging_dir = temp_dir_obj.name
        logger.debug(f"Using temporary staging directory: {staging_dir}")
    else:
        staging_dir = final_output_path

    # Define Paths for Components
    paths = {
        "modules": os.path.join(staging_dir, f"{prefix}_modules.txt"),
        "tests": os.path.join(staging_dir, f"{prefix}_tests.txt"),
        "resources": os.path.join(staging_dir, f"{prefix}_resources.txt"),
        "tree": tree_output_path if tree_output_path else os.path.join(staging_dir, f"{prefix}_tree.txt"),
        "errors": os.path.join(staging_dir, f"{prefix}_errors.txt"),
        "unified": os.path.join(staging_dir, f"{prefix}_full_context.txt"),
    }

    # Context bundle to pass to the next stage
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

    return None, env_context