from __future__ import annotations

"""
Parallel Transcription Management Stage.

Coordinates the multi-threaded transcription lifecycle by initializing 
filtering contexts, managing thread-safe I/O synchronization, and 
aggregating execution metrics. Acts as a bridge between the pipeline 
orchestrator and the concurrent execution engine.
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

# Local imports
from transcriptor4ai.application.common.file_filters import default_extensions
from transcriptor4ai.application.pipeline.stages.transcriber_context import (
    generate_config_hash,
    initialize_env,
)
from transcriptor4ai.application.pipeline.stages.transcriber_engine import execute_parallel_workers
from transcriptor4ai.application.services.project_scanner import ProjectScannerService
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.domain.ports.user_port import IUserContext

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API: TRANSCRIPTION ENTRANCE
# ==============================================================================

def transcribe_code(
    fs: IFileSystem,
    scanner_service: ProjectScannerService,
    cache_repo: ICacheRepository,
    user_context: IUserContext,
    input_path: str,
    modules_output_path: str,
    tests_output_path: str,
    resources_output_path: str,
    error_output_path: str,
    processing_depth: str = "full",
    process_tests: bool = True,
    process_resources: bool = False,
    extensions: Optional[List[str]] = None,
    include_patterns: Optional[List[str]] = None,
    exclude_patterns: Optional[List[str]] = None,
    respect_gitignore: bool = True,
    save_error_log: bool = True,
    enable_sanitizer: bool = True,
    mask_user_paths: bool = True,
    minify_output: bool = False,
    cancellation_event: Optional[threading.Event] = None,
) -> Dict[str, Any]:
    """
    Orchestrate parallel file transcription into categorized artifacts.

    Sequences environment bootstrapping, configuration fingerprinting for
    cache validation, and dispatching of atomic worker tasks.

    Args:
        fs: Abstracted file system implementation.
        scanner_service: Service for project discovery and classification.
        cache_repo: Persistent cache provider for incremental processing.
        user_context: OS-agnostic user metadata provider.
        input_path: Root project directory to process.
        modules_output_path: Destination for logic source code.
        tests_output_path: Destination for test suites.
        resources_output_path: Destination for documentation and config.
        error_output_path: Destination for technical failure reports.
        processing_depth: Level of detail (full, skeleton, tree_only).
        process_tests: Toggle for test inclusion.
        process_resources: Toggle for resource file inclusion.
        extensions: Whitelist of file extensions to process.
        include_patterns: List of regex strings for inclusion.
        exclude_patterns: List of regex strings for exclusion.
        respect_gitignore: Native .gitignore compliance flag.
        save_error_log: Persist failures to disk if True.
        enable_sanitizer: Execute PII and Secret redaction.
        mask_user_paths: Execute local path anonymization.
        minify_output: Strip code comments and redundant whitespace.
        cancellation_event: Signal to interrupt the active worker pool.

    Returns:
        Dict[str, Any]: Consolidated summary containing artifacts and metrics.
    """
    logger.info(f"Transcriber: Initiating parallel execution in: {input_path}")

    # 1. DISCOVERY: Prepare filtering context via the Project Scanner
    include_rx, exclude_rx = scanner_service.prepare_filtering_rules(
        input_path, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. ENVIRONMENT: Bootstrap output files and thread-safe locks
    locks, output_paths = initialize_env(
        fs,
        modules_output_path, tests_output_path, resources_output_path,
        error_output_path, processing_depth, process_tests, process_resources
    )

    # 3. INITIALIZATION: Setup metrics accumulator
    results: Dict[str, Any] = {
        "processed": 0,
        "cached": 0,
        "skipped": 0,
        "total_tokens": 0,
        "tests_written": 0,
        "modules_written": 0,
        "resources_written": 0,
        "errors": []
    }

    # 4. CACHING: Generate deterministic config fingerprint
    config_hash = generate_config_hash(
        processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output
    )

    # 5. EXECUTION: Dispatch workload to parallel worker pool
    execute_parallel_workers(
        scanner_service, input_path, extensions or default_extensions(),
        include_rx, exclude_rx, processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output,
        locks, output_paths, results,
        cache_repo, config_hash,
        user_context,
        cancellation_event
    )

    # 6. INTEGRITY: Verify early termination signals
    if cancellation_event and cancellation_event.is_set():
        logger.warning("Transcriber: Process interrupted by cancellation event.")
        return {"ok": False, "error": "Operation cancelled by user."}

    # 7. PERSISTENCE: Finalize technical error reporting
    actual_error_path = scanner_service.finalize_error_reporting(
        save_error_log, error_output_path, results["errors"]
    )

    # 8. SUMMARY: Compile execution statistics
    logger.info(
        f"Transcriber: Cycle complete. [Processed: {results['processed']}] "
        f"[Cached: {results['cached']}] [Errors: {len(results['errors'])}]"
    )

    return {
        "ok": True,
        "input_path": os.path.abspath(input_path),
        "generated": {
            "tests": tests_output_path if results["tests_written"] > 0 else "",
            "modules": modules_output_path if results["modules_written"] > 0 else "",
            "resources": resources_output_path if results["resources_written"] > 0 else "",
            "errors": actual_error_path,
        },
        "counters": {
            "processed": results["processed"],
            "cached": results["cached"],
            "skipped": results["skipped"],
            "total_tokens": results["total_tokens"],
            "tests_written": results["tests_written"],
            "modules_written": results["modules_written"],
            "resources_written": results["resources_written"],
            "errors": len(results["errors"]),
        },
    }