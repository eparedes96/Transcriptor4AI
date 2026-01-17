from __future__ import annotations

"""
Pipeline Assembler & Finalizer.

This module handles the final phase of the workflow:
1. Assembling the unified context file from partials.
2. Counting tokens of the final result.
3. Deploying files (move from staging to final).
4. Cleaning up temporary resources.
5. Generating the final PipelineResult summary.
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


def assemble_and_finalize(
        cfg: Dict[str, Any],
        trans_res: Dict[str, Any],
        tree_lines: List[str],
        env_context: Dict[str, Any],
        dry_run: bool
) -> PipelineResult:
    """
    Assemble files, calculate metrics, and deploy results.

    Args:
        cfg: The configuration dictionary.
        trans_res: Results from the transcription worker.
        tree_lines: Generated tree structure lines.
        env_context: Context dictionary from the setup phase.
        dry_run: Whether to simulate execution.

    Returns:
        PipelineResult: The final success object with summary statistics.
    """
    # Unpack context
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

    # -------------------------------------------------------------------------
    # Assembly: Unified File Creation
    # -------------------------------------------------------------------------
    if cfg["create_unified_file"]:
        try:
            with open(paths["unified"], "w", encoding="utf-8") as outfile:
                outfile.write(f"PROJECT CONTEXT: {os.path.basename(base_path)}\n")
                outfile.write("=" * 80 + "\n\n")

                if cfg["generate_tree"] and os.path.exists(paths["tree"]):
                    outfile.write("PROJECT STRUCTURE:\n")
                    outfile.write("-" * 50 + "\n")
                    with open(paths["tree"], "r", encoding="utf-8") as infile:
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
                with open(paths["unified"], "r", encoding="utf-8") as f:
                    full_text = f.read()

                    final_token_count = count_tokens(full_text, model=target_model)
                    logger.info(f"Estimated token count ({target_model}): {final_token_count}")
            except Exception as e:
                logger.warning(f"Failed to count tokens: {e}")

        except OSError as e:
            logger.error(f"Failed to process unified file in staging: {e}")

    # -------------------------------------------------------------------------
    # Deployment
    # -------------------------------------------------------------------------
    gen_files_map = trans_res.get("generated", {}).copy()

    if dry_run:
        logger.info("Dry run: Skipping file deployment to final destination.")
        if unified_created:
            gen_files_map["unified"] = "(Simulated: Unified Context File)"
    else:
        if unified_created:
            real_path_unified = os.path.join(final_output_path, f"{prefix}_full_context.txt")
            shutil.move(paths["unified"], real_path_unified)
            gen_files_map["unified"] = real_path_unified

        if os.path.exists(paths["errors"]) and staging_dir != final_output_path:
            shutil.move(paths["errors"], os.path.join(final_output_path, f"{prefix}_errors.txt"))

    # -------------------------------------------------------------------------
    # Cleanup & Finalize
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

    logger.info("Pipeline completed successfully.")
    return create_success_result(
        cfg, base_path, final_output_path, existing_files,
        trans_res, tree_lines, paths["tree"], final_token_count, summary
    )