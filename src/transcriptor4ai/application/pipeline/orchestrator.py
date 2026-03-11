from __future__ import annotations

"""
Core Pipeline Orchestrator.

Acts as the central coordinator for the transcription engine. It implements 
the system's primary use case by sequencing configuration validation, 
environment setup, parallel task execution, and final context assembly.

This orchestrator is infrastructure-agnostic, depending strictly on Domain 
Ports for I/O, Caching, and User Identity.
"""

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

# Application Services
from transcriptor4ai.application.analysis.tree_generator import generate_directory_tree

# Application Stages
from transcriptor4ai.application.pipeline.stages.assembler import assemble_and_finalize
from transcriptor4ai.application.pipeline.stages.setup import prepare_environment
from transcriptor4ai.application.pipeline.stages.transcriber import transcribe_code
from transcriptor4ai.application.pipeline.stages.validator import validate_config
from transcriptor4ai.application.services.project_scanner import ProjectScannerService

# ==============================================================================
# IMPORTS
# ==============================================================================
# Domain Ports and Entities
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult, create_error_result
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.domain.ports.user_port import IUserContext

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PIPELINE ORCHESTRATION
# ==============================================================================

def run_pipeline(
        fs: IFileSystem,
        cache: ICacheRepository,
        user_context: IUserContext,
        config: Optional[Dict[str, Any]],
        *,
        overwrite: bool = False,
        dry_run: bool = False,
        tree_output_path: Optional[str] = None,
        cancellation_event: Optional[threading.Event] = None,
) -> PipelineResult:
    """
    Execute the full project transcription pipeline.

    Args:
        fs: Concrete implementation of the FileSystem port.
        cache: Concrete implementation of the Cache repository port.
        user_context: Concrete implementation of the User Context port.
        config: Raw configuration parameters (untrusted).
        overwrite: Permission to overwrite existing files.
        dry_run: Simulation mode flag.
        tree_output_path: Optional path override for the tree file.
        cancellation_event: Signal to abort long-running tasks.

    Returns:
        PipelineResult: Standardized result object with metrics and artifact info.
    """
    logger.info("Pipeline: Execution sequence initiated.")

    # 1. VALIDATION: Sanitize and normalize input configuration
    cfg, warnings = validate_config(config, strict=False)

    for warning in warnings:
        logger.warning(f"Pipeline: Configuration constraint -> {warning}")

    # 2. SETUP: Prepare filesystem environment and detect collisions
    error_result, env_context = prepare_environment(fs, cfg, overwrite, dry_run, tree_output_path)

    if error_result:
        # Abort if environment is invalid or naming collisions occur
        return error_result

    # Extract execution parameters from the resolved context
    paths = env_context["paths"]
    base_path = env_context["base_path"]
    final_output_path = env_context["final_output_path"]
    temp_dir_obj = env_context["temp_dir_obj"]

    # 3. SERVICES: Initialize required application services
    scanner_service = ProjectScannerService(fs)

    # 4. EXECUTION: Run heavy I/O and Analysis tasks in parallel
    # max_workers=2 balances Tree Generation (CPU/IO) and Transcription (IO)
    tree_lines: List[str] = []
    trans_res: Dict[str, Any] = {}

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="PipelineExecutor") as executor:

        # 4.1 TASK: Structural Tree Generation (Static Analysis)
        future_tree = executor.submit(
            generate_directory_tree,
            fs=fs,
            input_path=base_path,
            mode="all",
            extensions=cfg.get("extensions", []),
            include_patterns=cfg.get("include_patterns", []),
            exclude_patterns=cfg.get("exclude_patterns", []),
            respect_gitignore=bool(cfg.get("respect_gitignore")),
            show_functions=bool(cfg.get("show_functions")),
            show_classes=bool(cfg.get("show_classes")),
            show_methods=bool(cfg.get("show_methods")),
            print_to_log=bool(cfg.get("print_tree")),
            save_path=paths.get("tree", "") if cfg.get("generate_tree") else "",
        )

        # 4.2 TASK: Categorized Source Transcription (Parallel IO)
        future_trans = executor.submit(
            transcribe_code,
            fs=fs,
            scanner_service=scanner_service,
            cache_repo=cache,
            user_context=user_context,
            input_path=base_path,
            modules_output_path=paths.get("modules", ""),
            tests_output_path=paths.get("tests", ""),
            resources_output_path=paths.get("resources", ""),
            error_output_path=paths.get("errors", ""),
            processing_depth=str(cfg.get("processing_depth", "full")),
            process_tests=bool(cfg.get("process_tests")),
            process_resources=bool(cfg.get("process_resources")),
            extensions=cfg.get("extensions", []),
            include_patterns=cfg.get("include_patterns", []),
            exclude_patterns=cfg.get("exclude_patterns", []),
            respect_gitignore=bool(cfg.get("respect_gitignore")),
            save_error_log=bool(cfg.get("save_error_log")),
            enable_sanitizer=bool(cfg.get("enable_sanitizer", True)),
            mask_user_paths=bool(cfg.get("mask_user_paths", True)),
            minify_output=bool(cfg.get("minify_output", False)),
            cancellation_event=cancellation_event,
        )

        # 5. SYNCHRONIZATION: Collect results from parallel tasks
        if cfg["generate_tree"]:
            tree_lines = future_tree.result()

        trans_res = future_trans.result()

    # 6. QUALITY CHECK: Verify transcription success
    if not trans_res.get("ok"):
        if temp_dir_obj:
            temp_dir_obj.cleanup()

        err_msg = trans_res.get('error', 'Unknown transcription failure.')
        logger.error(f"Pipeline: Aborted due to engine failure -> {err_msg}")
        return create_error_result(f"Pipeline error: {err_msg}", cfg, base_path, final_output_path)

    # 7. FINALIZATION: Assemble artifacts, count tokens and deploy
    # All I/O operations are delegated to the 'fs' port within this stage
    return assemble_and_finalize(fs, cfg, trans_res, tree_lines, env_context, dry_run)