from __future__ import annotations

"""
Parallel Transcription Orchestrator Stage.

Manages the multi-threaded transcription lifecycle. Coordinates environment 
initialization, concurrent task dispatching via the Scanner service, 
thread-safe writing, and final error aggregation.

Features:
- Port-based Cache Integration to skip unchanged files.
- Thread-safe output categorization (Modules/Tests/Resources).
- AST-based Skeleton Mode routing for Python files.
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from transcriptor4ai.application.pipeline.components.file_filters import default_extensions
from transcriptor4ai.application.pipeline.stages.transcriber_context import (
    generate_config_hash,
    initialize_env,
)
from transcriptor4ai.application.pipeline.stages.transcriber_engine import execute_parallel_workers
from transcriptor4ai.application.services.project_scanner import ProjectScannerService
from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.domain import IUserContext

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# STAGE: PARALLEL TRANSCRIBER
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
    Execute parallel transcription of project files into categorized text files.

    Args:
        scanner_service: Service responsible for discovery and filtering.
        cache_repo: Implementation of the ICacheRepository port.
        input_path: Source directory to scan.
        modules_output_path: Target path for source logic transcription.
        tests_output_path: Target path for test suites transcription.
        resources_output_path: Target path for resource files.
        error_output_path: Target path for the operation error log.
        processing_depth: Content depth strategy ("full", "skeleton", "tree_only").
        process_tests: Enable test file processing.
        process_resources: Enable resource file processing.
        extensions: Allowed file extensions.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        respect_gitignore: Enable automatic .gitignore parsing.
        save_error_log: Enable error persistence to disk.
        enable_sanitizer: Enable secret redaction.
        mask_user_paths: Enable local path anonymization.
        minify_output: Enable code minification.
        cancellation_event: Optional event to signal process termination.

    Returns:
        Dict[str, Any]: Summary containing status, paths, and execution counters.
    """
    logger.info(f"Transcriber: Initiating parallel execution in: {input_path}")

    # 1. SETUP: Prepare filtering context via the Scanner service
    include_rx, exclude_rx = scanner_service.prepare_filtering_rules(
        input_path, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. CONTEXT: Initialize output headers and thread synchronization locks
    locks, output_paths = initialize_env(
        fs,
        modules_output_path, tests_output_path, resources_output_path,
        error_output_path, processing_depth, process_tests, process_resources
    )

    # Accumulator for metrics and errors
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

    # 3. CACHE: Fingerprint the current configuration for hit detection
    config_hash = generate_config_hash(
        processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output
    )

    # 4. EXECUTION: Dispatch parallel tasks through the engine
    execute_parallel_workers(
        scanner_service, input_path, extensions or default_extensions(),
        include_rx, exclude_rx, processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output,
        locks, output_paths, results,
        cache_repo, config_hash,
        user_context,
        cancellation_event
    )

    # 5. VALIDATION: Check for early termination signals
    if cancellation_event and cancellation_event.is_set():
        logger.warning("Transcriber: Operation aborted by user signal.")
        return {"ok": False, "error": "Operation cancelled by user."}

    # 6. REPORTING: Persist collected errors via the Scanner service
    actual_error_path = scanner_service.finalize_error_reporting(
        save_error_log, error_output_path, results["errors"]
    )

    logger.info(
        f"Transcriber: Finalized. Processed: {results['processed']} "
        f"(Cached: {results['cached']}). Errors: {len(results['errors'])}"
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