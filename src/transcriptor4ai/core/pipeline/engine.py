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
import os
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.analysis.tree_generator import generate_directory_tree
from transcriptor4ai.core.pipeline.transcriber import transcribe_code
from transcriptor4ai.core.pipeline.validator import validate_config
from transcriptor4ai.core.processing.tokenizer import count_tokens
from transcriptor4ai.domain.pipeline_models import (
    PipelineResult,
    create_error_result,
    create_success_result
)
from transcriptor4ai.infra.fs import (
    check_existing_output_files,
    normalize_path,
    get_real_output_path,
)

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
    # 1) Config & Path Normalization
    # -------------------------------------------------------------------------
    cfg, warnings = validate_config(config, strict=False)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Warning: {warning}")

    fallback_base = os.getcwd()
    base_path = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid input directory: {base_path}"
        logger.error(msg)
        return create_error_result(msg, cfg, base_path)

    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), base_path)
    final_output_path = get_real_output_path(output_base_dir, cfg["output_subdir_name"])
    prefix = cfg["output_prefix"]

    # -------------------------------------------------------------------------
    # 2) Overwrite Check
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
        )

    # -------------------------------------------------------------------------
    # 3) Directory & Staging Preparation
    # -------------------------------------------------------------------------
    if not dry_run:
        try:
            os.makedirs(final_output_path, exist_ok=True)
        except OSError as e:
            msg = f"Failed to create output directory {final_output_path}: {e}"
            logger.critical(msg)
            return create_error_result(msg, cfg, base_path, final_output_path)

    temp_dir_obj = None
    if dry_run or not cfg["create_individual_files"]:
        temp_dir_obj = tempfile.TemporaryDirectory()
        staging_dir = temp_dir_obj.name
        logger.debug(f"Using temporary staging directory: {staging_dir}")
    else:
        staging_dir = final_output_path

    # Define Paths for Components
    path_modules = os.path.join(staging_dir, f"{prefix}_modules.txt")
    path_tests = os.path.join(staging_dir, f"{prefix}_tests.txt")
    path_resources = os.path.join(staging_dir, f"{prefix}_resources.txt")
    path_tree = tree_output_path if tree_output_path else os.path.join(staging_dir, f"{prefix}_tree.txt")
    path_errors = os.path.join(staging_dir, f"{prefix}_errors.txt")
    path_unified = os.path.join(staging_dir, f"{prefix}_full_context.txt")

    # -------------------------------------------------------------------------
    # 4) Execute Services in Parallel
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
            save_path=path_tree if cfg["generate_tree"] else "",
        )

        # Task B: Transcription
        future_trans = executor.submit(
            transcribe_code,
            input_path=base_path,
            modules_output_path=path_modules,
            tests_output_path=path_tests,
            resources_output_path=path_resources,
            error_output_path=path_errors,
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

    if not trans_res.get("ok"):
        if temp_dir_obj:
            temp_dir_obj.cleanup()
        err_msg = trans_res.get('error', 'Unknown transcription error')
        return create_error_result(f"Transcription failure: {err_msg}", cfg, base_path, final_output_path)

    # -------------------------------------------------------------------------
    # 5) Assembly & Metrics
    # -------------------------------------------------------------------------
    unified_created = False
    final_token_count = 0

    if cfg["create_unified_file"]:
        try:
            with open(path_unified, "w", encoding="utf-8") as outfile:
                outfile.write(f"PROJECT CONTEXT: {os.path.basename(base_path)}\n")
                outfile.write("=" * 80 + "\n\n")

                if cfg["generate_tree"] and os.path.exists(path_tree):
                    outfile.write("PROJECT STRUCTURE:\n")
                    outfile.write("-" * 50 + "\n")
                    with open(path_tree, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                for key in ["modules", "tests", "resources"]:
                    gen_path = trans_res.get("generated", {}).get(key)
                    if gen_path and os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as infile:
                            shutil.copyfileobj(infile, outfile)
                        outfile.write("\n\n")

            unified_created = True

            # Calculate Tokens
            try:
                target_model = cfg.get("target_model", "GPT-4o / GPT-5")
                with open(path_unified, "r", encoding="utf-8") as f:
                    full_text = f.read()
                    final_token_count = count_tokens(full_text, model=target_model)
                    logger.info(f"Estimated token count ({target_model}): {final_token_count}")
            except Exception as e:
                logger.warning(f"Failed to count tokens: {e}")

        except OSError as e:
            logger.error(f"Failed to process unified file in staging: {e}")

    # -------------------------------------------------------------------------
    # 6) Deployment
    # -------------------------------------------------------------------------
    gen_files_map = trans_res.get("generated", {}).copy()

    if dry_run:
        logger.info("Dry run: Skipping file deployment to final destination.")
        if unified_created:
            gen_files_map["unified"] = "(Simulated: Unified Context File)"
    else:
        if unified_created:
            real_path_unified = os.path.join(final_output_path, f"{prefix}_full_context.txt")
            shutil.move(path_unified, real_path_unified)
            gen_files_map["unified"] = real_path_unified

        if os.path.exists(path_errors) and staging_dir != final_output_path:
            shutil.move(path_errors, os.path.join(final_output_path, f"{prefix}_errors.txt"))

    # -------------------------------------------------------------------------
    # 7) Cleanup & Finalize
    # -------------------------------------------------------------------------
    if temp_dir_obj:
        temp_dir_obj.cleanup()
        logger.debug("Staging directory cleaned up.")

    if not cfg["create_individual_files"]:
        for k in ["modules", "tests", "resources"]:
            gen_files_map.pop(k, None)

    counters = trans_res.get("counters", {}) or {}
    summary = {
        "final_output_path": final_output_path,
        "processed": int(counters.get("processed", 0)),
        "skipped": int(counters.get("skipped", 0)),
        "errors": int(counters.get("errors", 0)),
        "token_count": final_token_count,
        "generated_files": gen_files_map,
        "tree": {
            "generated": bool(cfg.get("generate_tree")),
            "path": path_tree if (cfg["create_individual_files"] and not dry_run) else None,
            "lines": len(tree_lines),
        },
        "existing_files_before_run": list(existing_files),
        "unified_generated": unified_created,
        "dry_run": dry_run,
        "will_generate": list(files_to_check) if dry_run else [],
        "V1.5_performance": {
            "sanitizer": bool(cfg.get("enable_sanitizer")),
            "mask_paths": bool(cfg.get("mask_user_paths")),
            "minifier": bool(cfg.get("minify_output")),
            "parallel_engine": True
        }
    }

    logger.info("Pipeline completed successfully.")
    return create_success_result(
        cfg, base_path, final_output_path, existing_files,
        trans_res, tree_lines, path_tree, final_token_count, summary
    )