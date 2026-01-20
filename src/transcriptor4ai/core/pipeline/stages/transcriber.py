from __future__ import annotations

"""
Parallel Transcription Orchestrator.

Manages the multi-threaded transcription lifecycle. It coordinates
initialization, concurrent task dispatching via the Scanner service,
thread-safe writing, and final error aggregation.
Integrates CacheService to skip processing of unchanged files.
Migration to 'processing_depth' strategy for AST-based 
skeletonization routing.
"""

import hashlib
import json
import logging
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.core.pipeline.components.filters import default_extensions
from transcriptor4ai.core.pipeline.components.writer import initialize_output_file
from transcriptor4ai.core.pipeline.stages.worker import process_file_task
from transcriptor4ai.core.services.cache import CacheService
from transcriptor4ai.core.services.scanner import (
    finalize_error_reporting,
    prepare_filtering_rules,
    yield_project_files,
)
from transcriptor4ai.domain.transcription_models import TranscriptionError
from transcriptor4ai.infra.fs import safe_mkdir

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
    locks, output_paths = _initialize_execution_environment(
        modules_output_path, tests_output_path, resources_output_path,
        error_output_path, processing_depth, process_tests, process_resources
    )

    results: Dict[str, Any] = {
        "processed": 0,
        "cached": 0,
        "skipped": 0,
        "tests_written": 0,
        "modules_written": 0,
        "resources_written": 0,
        "errors": []
    }

    # Initialize Cache Service and compute config hash
    cache_service = CacheService()
    config_hash = _generate_config_hash(
        processing_depth, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output
    )

    _execute_parallel_transcription(
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
            "tests_written": results["tests_written"],
            "modules_written": results["modules_written"],
            "resources_written": results["resources_written"],
            "errors": len(results["errors"]),
        },
    }


# ==============================================================================
# PRIVATE HELPERS
# ==============================================================================

def _initialize_execution_environment(
        modules_path: str,
        tests_path: str,
        resources_path: str,
        error_path: str,
        processing_depth: str,
        process_tests: bool,
        process_resources: bool
) -> Tuple[Dict[str, threading.Lock], Dict[str, str]]:
    """Initialize output directory structure, file headers, and thread locks."""
    for p in [modules_path, tests_path, resources_path, error_path]:
        safe_mkdir(os.path.dirname(os.path.abspath(p)))

    # Thread locks ensure that multiple workers don't corrupt the shared output files
    locks = {
        "module": threading.Lock(),
        "test": threading.Lock(),
        "resource": threading.Lock(),
        "error": threading.Lock()
    }

    output_paths = {
        "module": modules_path,
        "test": tests_path,
        "resource": resources_path,
        "error": error_path
    }

    # Only initialize module file if depth is not tree_only
    if processing_depth != "tree_only":
        initialize_output_file(modules_path, "SCRIPTS/MODULES:")
    if process_tests:
        initialize_output_file(tests_path, "TESTS:")
    if process_resources:
        initialize_output_file(resources_path, "RESOURCES (CONFIG/DATA/DOCS):")

    return locks, output_paths


def _generate_config_hash(*args: Any) -> str:
    """Generate a unique fingerprint for the current processing configuration."""
    raw = json.dumps(args, sort_keys=True)
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def _execute_parallel_transcription(
        input_path: str,
        extensions: List[str],
        include_rx: List[re.Pattern],
        exclude_rx: List[re.Pattern],
        processing_depth: str,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        results: Dict[str, Any],
        cache_service: CacheService,
        config_hash: str,
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """Consumes the Scanner's generator, manages Caching, and dispatches workers."""
    tasks = []

    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:

        # Legacy backward compatibility check for Scanner
        process_modules_flag = processing_depth != "tree_only"

        for file_data in yield_project_files(
                input_path=input_path,
                extensions=extensions,
                include_rx=include_rx,
                exclude_rx=exclude_rx,
                process_modules=process_modules_flag,
                process_tests=process_tests,
                process_resources=process_resources
        ):
            if cancellation_event and cancellation_event.is_set():
                break

            if file_data.get("status") == "skipped":
                results["skipped"] += 1
                continue

            if file_data.get("status") == "process":
                f_path = file_data["file_path"]

                # Cache Hit Check
                try:
                    stat = os.stat(f_path)
                    comp_hash = cache_service.compute_composite_hash(
                        f_path, stat.st_mtime, stat.st_size, config_hash
                    )
                    cached_content = cache_service.get_entry(comp_hash)

                    if cached_content is not None:
                        _write_cached_content(
                            cached_content,
                            file_data,
                            locks,
                            output_paths,
                            processing_depth,
                            process_tests,
                            process_resources
                        )
                        results["processed"] += 1
                        results["cached"] += 1
                        continue

                except OSError:
                    comp_hash = ""

                # Dispatch Worker
                tasks.append(executor.submit(
                    process_file_task,
                    file_path=f_path,
                    rel_path=file_data["rel_path"],
                    ext=file_data["ext"],
                    file_name=file_data["file_name"],
                    processing_depth=processing_depth,
                    process_tests=process_tests,
                    process_resources=process_resources,
                    enable_sanitizer=enable_sanitizer,
                    mask_user_paths=mask_user_paths,
                    minify_output=minify_output,
                    locks=locks,
                    output_paths=output_paths,
                    composite_hash=comp_hash
                ))

        # Synchronize and aggregate worker results
        for future in as_completed(tasks):
            if cancellation_event and cancellation_event.is_set():
                continue

            worker_res = future.result()
            if worker_res["ok"]:
                results["processed"] += 1
                mode = worker_res.get("mode")

                # Update Cache if worker returned content + hash
                if worker_res.get("processed_content") and worker_res.get("composite_hash"):
                    cache_service.set_entry(
                        worker_res["composite_hash"],
                        worker_res["file_path"],
                        worker_res["processed_content"]
                    )

                if mode == "test":
                    results["tests_written"] += 1
                elif mode == "module":
                    results["modules_written"] += 1
                elif mode == "resource":
                    results["resources_written"] += 1
            else:
                results["errors"].append(TranscriptionError(
                    rel_path=worker_res["rel_path"],
                    error=worker_res["error"]
                ))


def _write_cached_content(
        content: str,
        file_data: Dict[str, Any],
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        processing_depth: str,
        process_tests: bool,
        process_resources: bool
) -> None:
    """Helper to write retrieved cache content respecting headers and locks."""
    from transcriptor4ai.core.pipeline.components.filters import is_resource_file, is_test

    file_name = file_data["file_name"]
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    # Routing logic based on new processing_depth
    if processing_depth != "tree_only":
        if file_is_test:
            if process_tests:
                target_mode = "test"
        elif file_is_resource:
            if process_resources:
                target_mode = "resource"
            else:
                target_mode = "module"
        else:
            target_mode = "module"

    if target_mode == "skip":
        return

    separator = "-" * 200
    lock = locks.get(target_mode)
    out_path = output_paths.get(target_mode)

    if lock and out_path:
        with lock:
            with open(out_path, "a", encoding="utf-8") as out:
                out.write(f"{separator}\n")
                out.write(f"{file_data['rel_path']}\n")
                out.write(content)
                out.write("\n")