from __future__ import annotations

"""
Pipeline Assembler & Finalizer Stage.

Orchestrates the terminal phase of the transcription workflow by coordinating:
1. Aggregation of categorized staging files into a unified AI context.
2. High-precision token estimation of the final result.
3. Atomic deployment of artifacts from staging to user-defined destinations.
4. Resource disposal and standardized result generation.
"""

import logging
from typing import Any, Dict, List

from transcriptor4ai.application.processing.token_service import count_tokens
from transcriptor4ai.domain.entities.pipeline_results import (
    PipelineResult,
    create_success_result,
)
from transcriptor4ai.domain.ports.system_port import IFileSystem

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# STAGE: PIPELINE ASSEMBLER
# ==============================================================================

def assemble_and_finalize(
        fs: IFileSystem,
        cfg: Dict[str, Any],
        trans_res: Dict[str, Any],
        tree_lines: List[str],
        env_context: Dict[str, Any],
        dry_run: bool
) -> PipelineResult:
    """
    Finalize the transcription cycle and package results for the interface.

    Args:
        fs: Injected implementation of the FileSystem port.
        cfg: Validated configuration dictionary.
        trans_res: Metadata and paths from transcription workers.
        tree_lines: visual lines representing the directory structure.
        env_context: Environment state (paths, staging objects).
        dry_run: If True, skips physical artifact deployment.

    Returns:
        PipelineResult: Standardized execution metrics and artifact locations.
    """
    # 1. SETUP: Extract environment variables and paths
    final_output_path = env_context["final_output_path"]
    temp_dir_obj = env_context["temp_dir_obj"]
    paths = env_context["paths"]

    unified_created = False
    final_token_count = 0

    # ==========================================================================
    # PHASE 1: CONTEXT AGGREGATION
    # ==========================================================================
    if cfg["create_unified_file"]:
        # 1.1 MERGE: Instruct the adapter to concatenate staging files
        # The adapter handles formatting and streaming buffers
        unified_created = fs.generate_unified_file(
            output_path=paths["unified"],
            base_path=env_context["base_path"],
            tree_path=paths["tree"] if cfg["generate_tree"] else None,
            category_paths=trans_res.get("generated", {})
        )

        # 1.2 METRICS: Calculate final token density for the AI context
        if unified_created:
            try:
                target_model = cfg.get("target_model", "- Default Model -")
                content = fs.read_file_content(paths["unified"])
                final_token_count = count_tokens(content, model=target_model)
                logger.info(f"Assembler: Token density verified ({final_token_count})")
            except Exception as e:
                logger.warning(f"Assembler: Precision token count failed: {e}")

    # ==========================================================================
    # PHASE 2: ARTIFACT DEPLOYMENT
    # ==========================================================================
    gen_files_map = trans_res.get("generated", {}).copy()

    if dry_run:
        logger.info("Assembler: Dry run mode. Deployment bypassed.")
        if unified_created:
            gen_files_map["unified"] = "(Simulated: Unified Context File)"
    else:
        # 2.1 DEPLOY: Move artifacts from staging/temp to final destination
        fs.deploy_pipeline_artifacts(
            staging_paths=paths,
            final_dir=final_output_path,
            prefix=env_context["prefix"],
            unified_ok=unified_created,
            results_map=gen_files_map
        )

    # ==========================================================================
    # PHASE 3: FINALIZATION
    # ==========================================================================
    # 3.1 CLEANUP: Dispose of temporary staging resources
    if temp_dir_obj:
        temp_dir_obj.cleanup()
        logger.debug("Assembler: Staging resources successfully released.")

    # 3.2 FILTER: Cleanup results map if individual files were suppressed
    if not cfg["create_individual_files"]:
        for k in ["modules", "tests", "resources"]:
            gen_files_map.pop(k, None)

    # 3.3 RESULT: Delegate summary construction and return standardized Result
    logger.info("Assembler: Transcription cycle finalized.")

    return create_success_result(
        cfg=cfg,
        base_path=env_context["base_path"],
        final_output_path=final_output_path,
        existing_files=env_context["existing_files"],
        trans_res=trans_res,
        tree_lines=tree_lines,
        tree_path=paths.get("tree", ""),
        token_count=final_token_count,
        generated_files=gen_files_map,
        dry_run=dry_run
    )