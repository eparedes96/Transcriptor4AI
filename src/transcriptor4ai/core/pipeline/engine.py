from __future__ import annotations

"""
Core Pipeline Orchestrator.

Acts as the central Facade for the transcription engine. It coordinates the 
entire workflow lifecycle: configuration validation, environment setup, 
parallel task execution (scanning and transcription), and final assembly 
of results into a unified AI context.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.analysis.tree_generator import generate_directory_tree
from transcriptor4ai.core.pipeline.stages.assembler import assemble_and_finalize
from transcriptor4ai.core.pipeline.stages.setup import prepare_environment
from transcriptor4ai.core.pipeline.stages.transcriber import transcribe_code
from transcriptor4ai.core.pipeline.stages.validator import validate_config
from transcriptor4ai.domain.pipeline_models import PipelineResult, create_error_result

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PIPELINE ORCHESTRATION
# -----------------------------------------------------------------------------

def run_pipeline(
        config: Optional[Dict[str, Any]],
        *,
        overwrite: bool = False,
        dry_run: bool = False,
        tree_output_path: Optional[str] = None,
        cancellation_event: Optional[threading.Event] = None,
) -> PipelineResult:
    """
    Execute the full project transcription pipeline.

    Orchestrates specialized stages in parallel using a ThreadPoolExecutor
    to optimize I/O and CPU-bound operations. Aggregates results into a
    standardized domain model.

    Args:
        config: Raw configuration parameters.
        overwrite: Permission to overwrite existing files at destination.
        dry_run: Simulation mode (calculates tokens, skips file deployment).
        tree_output_path: Optional path override for the structure tree.
        cancellation_event: Optional event to signal process termination.

    Returns:
        PipelineResult: Final execution result containing metrics and summary.
    """
    logger.info("Pipeline execution sequence started.")

    # 1. Validation Stage: Schema enforcement
    cfg, warnings = validate_config(config, strict=False)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Constraint: {warning}")

    # 2. Setup Stage: Environment initialization and safety checks
    error_result, env_context = prepare_environment(cfg, overwrite, dry_run, tree_output_path)

    if error_result:
        return error_result

    # Extraction of environment parameters for parallel execution
    paths = env_context["paths"]
    base_path = env_context["base_path"]
    final_output_path = env_context["final_output_path"]
    temp_dir_obj = env_context["temp_dir_obj"]

    # 3. Execution Stage: Parallel processing of Tree and Transcription
    tree_lines: List[str] = []
    trans_res: Dict[str, Any] = {}

    # Parallelization of I/O heavy tasks
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="PipelineExecutor") as executor:

        # Sub-Task: Structural Tree Generation (Static Analysis)
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

        # Sub-Task: Sequential Transcription (Transformation Pipeline)
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
            cancellation_event=cancellation_event,
        )

        # Synchronize and collect task results
        if cfg["generate_tree"]:
            tree_lines = future_tree.result()

        trans_res = future_trans.result()

    # 4. Error Management Phase
    if not trans_res.get("ok"):
        if temp_dir_obj:
            temp_dir_obj.cleanup()
        err_msg = trans_res.get('error', 'Critical transcription failure.')
        return create_error_result(f"Pipeline error: {err_msg}", cfg, base_path, final_output_path)

    # 5. Finalization Stage: Assembly and Deployment
    return assemble_and_finalize(cfg, trans_res, tree_lines, env_context, dry_run)