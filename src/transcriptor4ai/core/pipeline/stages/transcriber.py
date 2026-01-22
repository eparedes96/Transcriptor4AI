from __future__ import annotations

from transcriptor4ai.core.pipeline.stages.transcriber_context import initialize_env, \
    generate_config_hash
from transcriptor4ai.core.pipeline.stages.transcriber_engine import execute_parallel_workers

"""
Parallel Transcription Orchestrator.

Manages the multi-threaded transcription lifecycle. It coordinates
initialization, concurrent task dispatching via the Scanner service,
thread-safe writing, and final error aggregation.
Integrates CacheService to skip processing of unchanged files.
Migration to 'processing_depth' strategy for AST-based 
skeletonization routing.
"""

import logging
import os
import threading
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.pipeline.components.filters import default_extensions
from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.scanner import (
    finalize_error_reporting,
    prepare_filtering_rules,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API
# ==============================================================================

def transcribe_code(
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
        cancellation_event: Optional[threading.Event] = None
) -> Dict[str, Any]:
    """
    Execute parallel transcription of project files into categorized text files.

    Acts as the high-level orchestrator. It prepares the environment,
    delegates file discovery to the Scanner service, manages worker threads,
    and handles the caching strategy to optimize re-runs.

    Args:
        input_path: Source directory to scan.
        modules_output_path: Target path for source logic transcription.
        tests_output_path: Target path for test suites transcription.
        resources_output_path: Target path for configuration/documentation files.
        error_output_path: Target path for the operation error log.
        processing_depth: Content depth strategy ("full", "skeleton", "tree_only").
        process_tests: Enable test file processing.
        process_resources: Enable resource file processing.
        extensions: Filter by specific file extensions.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        respect_gitignore: Enable automatic .gitignore parsing.
        save_error_log: Enable error persistence to disk.
        enable_sanitizer: Enable secret redaction.
        mask_user_paths: Enable local path anonymization.
        minify_output: Enable code minification.
        cancellation_event: Optional event to signal process termination.

    Returns:
        Dict[str, Any]: Execution summary containing status, generated paths, and counters.
    """
    logger.info(f"Initiating parallel transcription in: {input_path}")

    # 1. Delegate filtering rule preparation to Scanner
    include_rx, exclude_rx = prepare_filtering_rules(
        input_path, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. Setup output files and thread synchronization locks
    locks, output_paths = initialize_env(
        modules_output_path, tests_output_path, resources_output_path,
        error_output_path, processing_depth, process_tests, process_resources
    )

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

    # Initialize Cache Service and compute config hash
    cache_service = CacheService()
    config_hash = generate_config_hash(
        processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output
    )

    execute_parallel_workers(
        input_path, extensions or default_extensions(), include_rx, exclude_rx,
        processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output,
        locks, output_paths, results,
        cache_service, config_hash,
        cancellation_event
    )

    if cancellation_event and cancellation_event.is_set():
        logger.warning("Parallel Transcription aborted by user signal.")
        return {"ok": False, "error": "Operation cancelled by user."}

    # 4. Delegate final reporting to Scanner
    actual_error_path = finalize_error_reporting(
        save_error_log, error_output_path, results["errors"]
    )

    logger.info(
        f"Parallel Transcription finalized. "
        f"Processed: {results['processed']} (Cached: {results['cached']}). "
        f"Errors: {len(results['errors'])}"
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