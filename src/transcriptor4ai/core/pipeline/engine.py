from __future__ import annotations

"""
Core orchestration pipeline.

This module coordinates the entire transcription workflow:
1. Validates configuration and paths.
2. Checks for overwrite conflicts.
3. Prepares output directories (or staging areas).
4. Executes Transcription and Tree Generation in parallel threads.
5. Assembles unified context files.
6. Computes token metrics.
7. Deploys final files to the destination.
"""

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.analysis.tree_generator import generate_directory_tree
from transcriptor4ai.core.pipeline.stages.transcriber import transcribe_code
from transcriptor4ai.core.pipeline.stages.validator import validate_config
from transcriptor4ai.domain.pipeline_models import (
    PipelineResult,
    create_error_result
)

from transcriptor4ai.core.pipeline.stages.setup import prepare_environment
from transcriptor4ai.core.pipeline.stages.assembler import assemble_and_finalize

logger = logging.getLogger(__name__)


def run_pipeline(
        config: Optional[Dict[str, Any]],
        *,
        overwrite: bool = False,
        dry_run: bool = False,
        tree_output_path: Optional[str] = None,
) -> PipelineResult:
    """
    Execute the full transcription pipeline.

    Orchestrates services in parallel to reduce I/O wait times and
    aggregates results into a unified structure.

    Args:
        config: The configuration dictionary (raw or partial).
        overwrite: If True, overwrite existing output files.
        dry_run: If True, simulate execution without writing to disk.
        tree_output_path: Optional override path for the tree file.

    Returns:
        PipelineResult: Object containing status, metrics, and summary.
    """
    logger.info("Pipeline execution started.")

    # -------------------------------------------------------------------------
    # 1) Validation
    # -------------------------------------------------------------------------
    cfg, warnings = validate_config(config, strict=False)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Warning: {warning}")

    # -------------------------------------------------------------------------
    # 2) Environment Setup & Safety Checks
    # -------------------------------------------------------------------------
    error_result, env_context = prepare_environment(cfg, overwrite, dry_run, tree_output_path)

    if error_result:
        return error_result

    # Unpack paths for workers
    paths = env_context["paths"]
    base_path = env_context["base_path"]
    final_output_path = env_context["final_output_path"]
    temp_dir_obj = env_context["temp_dir_obj"]

    # -------------------------------------------------------------------------
    # 3) Parallel Execution (Tree & Transcription)
    # -------------------------------------------------------------------------
    tree_lines: List[str] = []
    trans_res: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="PipelineExecutor") as executor:
        # Task A: Tree Generation
        future_tree = executor.submit(
            generate_directory_tree,
            input_path=base_path,
            mode="all",
            extensions=cfg["extensions"],
            include_patterns=cfg["include_patterns"],
            exclude_patterns=cfg["exclude_patterns"],
            respect_gitignore=bool(cfg.get("respect_gitignore")),
            show_functions=bool(cfg.get("show_functions")),
            show_classes=bool(cfg.get("show_classes")),
            show_methods=bool(cfg.get("show_methods")),
            print_to_log=bool(cfg.get("print_tree")),
            save_path=paths["tree"] if cfg["generate_tree"] else "",
        )

        # Task B: Transcription
        future_trans = executor.submit(
            transcribe_code,
            input_path=base_path,
            modules_output_path=paths["modules"],
            tests_output_path=paths["tests"],
            resources_output_path=paths["resources"],
            error_output_path=paths["errors"],
            process_modules=bool(cfg["process_modules"]),
            process_tests=bool(cfg["process_tests"]),
            process_resources=bool(cfg["process_resources"]),
            extensions=cfg["extensions"],
            include_patterns=cfg["include_patterns"],
            exclude_patterns=cfg["exclude_patterns"],
            respect_gitignore=bool(cfg["respect_gitignore"]),
            save_error_log=bool(cfg["save_error_log"]),
            enable_sanitizer=bool(cfg.get("enable_sanitizer", True)),
            mask_user_paths=bool(cfg.get("mask_user_paths", True)),
            minify_output=bool(cfg.get("minify_output", False)),
        )

        # Collect results
        if cfg["generate_tree"]:
            tree_lines = future_tree.result()

        trans_res = future_trans.result()

    # -------------------------------------------------------------------------
    # 4) Error Handling
    # -------------------------------------------------------------------------
    if not trans_res.get("ok"):
        if temp_dir_obj:
            temp_dir_obj.cleanup()
        err_msg = trans_res.get('error', 'Unknown transcription error')
        return create_error_result(f"Transcription failure: {err_msg}", cfg, base_path, final_output_path)

    # -------------------------------------------------------------------------
    # 5) Assembly & Finalization
    # -------------------------------------------------------------------------
    return assemble_and_finalize(cfg, trans_res, tree_lines, env_context, dry_run)