from __future__ import annotations

"""
Parallel Transcription Orchestrator.

Manages the multi-threaded transcription lifecycle. It coordinates 
initialization, concurrent task dispatching via the Scanner service, 
thread-safe writing, and final error aggregation.
"""

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.core.pipeline.components.filters import default_extensions
from transcriptor4ai.core.pipeline.components.writer import initialize_output_file
from transcriptor4ai.core.pipeline.stages.worker import process_file_task
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
        process_modules: bool = True,
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
    delegates file discovery to the Scanner service, and manages worker threads.

    Args:
        input_path: Source directory to scan.
        modules_output_path: Target path for source logic transcription.
        tests_output_path: Target path for test suites transcription.
        resources_output_path: Target path for configuration/documentation files.
        error_output_path: Target path for the operation error log.
        process_modules: Enable source code processing.
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
        error_output_path, process_modules, process_tests, process_resources
    )

    results: Dict[str, Any] = {
        "processed": 0,
        "skipped": 0,
        "tests_written": 0,
        "modules_written": 0,
        "resources_written": 0,
        "errors": []
    }

    # 3. Perform concurrent processing using the Scanner's generator
    _execute_parallel_transcription(
        input_path, extensions or default_extensions(), include_rx, exclude_rx,
        process_modules, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output,
        locks, output_paths, results, cancellation_event
    )

    if cancellation_event and cancellation_event.is_set():
        logger.warning("Parallel Transcription aborted by user signal.")
        return {"ok": False, "error": "Operation cancelled by user."}

    # 4. Delegate final reporting to Scanner
    actual_error_path = finalize_error_reporting(
        save_error_log, error_output_path, results["errors"]
    )

    logger.info(
        f"Parallel Transcription finalized. Processed: {results['processed']}. "
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
        process_modules: bool,
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

    if process_modules:
        initialize_output_file(modules_path, "SCRIPTS/MODULES:")
    if process_tests:
        initialize_output_file(tests_path, "TESTS:")
    if process_resources:
        initialize_output_file(resources_path, "RESOURCES (CONFIG/DATA/DOCS):")

    return locks, output_paths


def _execute_parallel_transcription(
        input_path: str,
        extensions: List[str],
        include_rx: List[Any],
        exclude_rx: List[Any],
        process_modules: bool,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        results: Dict[str, Any],
        cancellation_event: Optional[threading.Event] = None
) -> None:
    """Consumes the Scanner's generator and dispatches tasks to the worker pool."""
    tasks = []

    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:
        # Use the decoupled Scanner service to find files
        for file_data in yield_project_files(
            input_path=input_path,
            extensions=extensions,
            include_rx=include_rx,
            exclude_rx=exclude_rx,
            process_modules=process_modules,
            process_tests=process_tests,
            process_resources=process_resources
        ):
            if cancellation_event and cancellation_event.is_set():
                break

            tasks.append(executor.submit(
                process_file_task,
                file_path=file_data["file_path"],
                rel_path=file_data["rel_path"],
                ext=file_data["ext"],
                file_name=file_data["file_name"],
                process_modules=process_modules,
                process_tests=process_tests,
                process_resources=process_resources,
                enable_sanitizer=enable_sanitizer,
                mask_user_paths=mask_user_paths,
                minify_output=minify_output,
                locks=locks,
                output_paths=output_paths
            ))

        # Synchronize and aggregate worker results
        for future in as_completed(tasks):
            if cancellation_event and cancellation_event.is_set():
                continue

            worker_res = future.result()
            if worker_res["ok"]:
                results["processed"] += 1
                mode = worker_res.get("mode")
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