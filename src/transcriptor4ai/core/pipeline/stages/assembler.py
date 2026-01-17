from __future__ import annotations

"""
Pipeline Assembler & Finalizer Stage.

Orchestrates the terminal phase of the transcription workflow:
1. Unified context aggregation from partial transcription files.
2. Context-aware token counting using the hybrid strategy.
3. Atomic deployment from staging/temporary areas to final destinations.
4. Final metrics generation and resource cleanup.
"""

import logging
import os
import shutil
from typing import Any, Dict, List

from transcriptor4ai.core.processing.tokenizer import count_tokens
from transcriptor4ai.domain.pipeline_models import (
    PipelineResult,
    create_success_result
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# CORE ASSEMBLY LOGIC
# -----------------------------------------------------------------------------

def assemble_and_finalize(
        cfg: Dict[str, Any],
        trans_res: Dict[str, Any],
        tree_lines: List[str],
        env_context: Dict[str, Any],
        dry_run: bool
) -> PipelineResult:
    """
    Perform final assembly of artifacts, compute metrics, and deploy results.

    Coordinates the transition from intermediate staging files to the
    user-facing output directory. Handles token estimation and ensures
    temporary resources are released.

    Args:
        cfg: Validated configuration dictionary.
        trans_res: Dictionary containing results from the transcription workers.
        tree_lines: Visual directory tree generated in previous stages.
        env_context: Execution environment context (paths, staging info).
        dry_run: If True, skips physical deployment to final paths.

    Returns:
        PipelineResult: Success object containing summary and execution metadata.
    """
    # Unpack environment context provided by the setup stage
    base_path = env_context["base_path"]
    final_output_path = env_context["final_output_path"]
    staging_dir = env_context["staging_dir"]
    temp_dir_obj = env_context["temp_dir_obj"]
    prefix = env_context["prefix"]
    paths = env_context["paths"]
    existing_files = env_context["existing_files"]
    files_to_check = env_context["files_to_check"]

    unified_created = False
    final_token_count = 0

    # -----------------------------------------------------------------------------
    # PHASE 1: UNIFIED CONTEXT AGGREGATION
    # -----------------------------------------------------------------------------
    if cfg["create_unified_file"]:
        try:
            with open(paths["unified"], "w", encoding="utf-8") as outfile:
                # Header Section
                outfile.write(f"PROJECT CONTEXT: {os.path.basename(base_path)}\n")
                outfile.write("=" * 80 + "\n\n")

                # Structure Section (Directory Tree)
                if cfg["generate_tree"] and os.path.exists(paths["tree"]):
                    outfile.write("PROJECT STRUCTURE:\n")
                    outfile.write("-" * 50 + "\n")
                    with open(paths["tree"], "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                # Content Sections (Modules, Tests, Resources)
                for key in ["modules", "tests", "resources"]:
                    gen_path = trans_res.get("generated", {}).get(key)
                    if gen_path and os.path.exists(gen_path):
                        with open(gen_path, "r", encoding="utf-8") as infile:
                            shutil.copyfileobj(infile, outfile)
                        outfile.write("\n\n")

            unified_created = True

            # Calculate token metrics for the unified context
            try:
                target_model = cfg.get("target_model", "GPT-4o / GPT-5")
                with open(paths["unified"], "r", encoding="utf-8") as f:
                    full_text = f.read()

                    final_token_count = count_tokens(full_text, model=target_model)
                    logger.info(f"Estimated token count ({target_model}): {final_token_count}")
            except Exception as e:
                logger.warning(f"Failed to count tokens: {e}")

        except OSError as e:
            logger.error(f"Failed to process unified file in staging: {e}")

    # -----------------------------------------------------------------------------
    # PHASE 2: ARTIFACT DEPLOYMENT (STAGING -> FINAL)
    # -----------------------------------------------------------------------------
    gen_files_map = trans_res.get("generated", {}).copy()

    if dry_run:
        logger.info("Dry run enabled: Skipping physical deployment of artifacts.")
        if unified_created:
            gen_files_map["unified"] = "(Simulated: Unified Context File)"
    else:
        # Move unified context to the final destination directory
        if unified_created:
            real_path_unified = os.path.join(final_output_path, f"{prefix}_full_context.txt")
            shutil.move(paths["unified"], real_path_unified)
            gen_files_map["unified"] = real_path_unified

        # Deploy error logs if they were generated in a staging area
        if os.path.exists(paths["errors"]) and staging_dir != final_output_path:
            shutil.move(paths["errors"], os.path.join(final_output_path, f"{prefix}_errors.txt"))

    # -----------------------------------------------------------------------------
    # PHASE 3: RESOURCE CLEANUP AND SUMMARY
    # -----------------------------------------------------------------------------
    # Dispose of temporary staging directory if it was created
    if temp_dir_obj:
        temp_dir_obj.cleanup()
        logger.debug("Temporary staging resources cleaned up.")

    # Filter out individual file paths if only unified output was requested
    if not cfg["create_individual_files"]:
        for k in ["modules", "tests", "resources"]:
            gen_files_map.pop(k, None)

    counters = trans_res.get("counters", {}) or {}

    # Construct technical execution summary
    summary = {
        "final_output_path": final_output_path,
        "processed": int(counters.get("processed", 0)),
        "skipped": int(counters.get("skipped", 0)),
        "errors": int(counters.get("errors", 0)),
        "token_count": final_token_count,
        "generated_files": gen_files_map,
        "tree": {
            "generated": bool(cfg.get("generate_tree")),
            "path": paths["tree"] if (cfg["create_individual_files"] and not dry_run) else None,
            "lines": len(tree_lines),
        },
        "existing_files_before_run": list(existing_files),
        "unified_generated": unified_created,
        "dry_run": dry_run,
        "will_generate": list(files_to_check) if dry_run else [],
        "V2.0_performance": {
            "sanitizer": bool(cfg.get("enable_sanitizer")),
            "mask_paths": bool(cfg.get("mask_user_paths")),
            "minifier": bool(cfg.get("minify_output")),
            "hybrid_tokenizer": True
        }
    }

    logger.info("Pipeline execution finalized successfully.")
    return create_success_result(
        cfg, base_path, final_output_path, existing_files,
        trans_res, tree_lines, paths["tree"], final_token_count, summary
    )