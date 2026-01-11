from __future__ import annotations

"""
Parallel Transcription Manager.

This module orchestrates the multi-threaded scanning and transcription process.
It initializes worker threads, manages file locks, and aggregates the results
into a structured report.
"""

import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.pipeline.filters import (
    compile_patterns,
    default_extensions,
    default_exclude_patterns,
    default_include_patterns,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)
from transcriptor4ai.core.pipeline.worker import process_file_task
from transcriptor4ai.core.pipeline.writer import initialize_output_file
from transcriptor4ai.domain.transcription_models import TranscriptionError
from transcriptor4ai.infra.fs import _safe_mkdir

logger = logging.getLogger(__name__)


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
) -> Dict[str, Any]:
    """
    Consolidate source code and resources into specific text files using parallel workers.

    Args:
        input_path: Source directory to scan.
        modules_output_path: Destination path for source code (scripts).
        tests_output_path: Destination path for test code.
        resources_output_path: Destination path for resources (docs/config).
        error_output_path: Destination path for error log.
        process_modules: If True, extract source code files.
        process_tests: If True, extract test files.
        process_resources: If True, extract resource files.
        extensions: List of allowed file extensions.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        respect_gitignore: If True, parse .gitignore.
        save_error_log: Whether to write the error log file.
        enable_sanitizer: If True, redact secrets from the output.
        mask_user_paths: If True, anonymize local user paths.
        minify_output: If True, remove redundant code comments.

    Returns:
        Dict[str, Any]: A dictionary containing counters, paths, and execution status.
    """
    logger.info(f"Starting parallel transcription scan in: {input_path}")

    # 1. Normalization & Setup
    if extensions is None:
        extensions = default_extensions()
    if include_patterns is None:
        include_patterns = default_include_patterns()
    if exclude_patterns is None:
        exclude_patterns = default_exclude_patterns()

    input_path_abs = os.path.abspath(input_path)

    for p in [modules_output_path, tests_output_path, resources_output_path, error_output_path]:
        _safe_mkdir(os.path.dirname(os.path.abspath(p)))

    # 2. Pattern Compilation
    final_exclusions = list(exclude_patterns)
    if respect_gitignore:
        git_patterns = load_gitignore_patterns(input_path_abs)
        if git_patterns:
            logger.debug(f"Loaded {len(git_patterns)} patterns from .gitignore")
            final_exclusions.extend(git_patterns)

    include_rx = compile_patterns(include_patterns)
    exclude_rx = compile_patterns(final_exclusions)

    # 3. Threading Infrastructure
    # We use locks to ensure only one thread writes to a specific file at a time
    locks = {
        "module": threading.Lock(),
        "test": threading.Lock(),
        "resource": threading.Lock(),
        "error": threading.Lock()
    }

    output_paths = {
        "module": modules_output_path,
        "test": tests_output_path,
        "resource": resources_output_path,
        "error": error_output_path
    }

    # Tracking shared across workers (protected by local logic/locks)
    results = {
        "processed": 0,
        "skipped": 0,
        "tests_written": 0,
        "modules_written": 0,
        "resources_written": 0,
        "errors": []
    }

    # Pre-initialize headers
    if process_modules:
        initialize_output_file(modules_output_path, "SCRIPTS/MODULES:")
    if process_tests:
        initialize_output_file(tests_output_path, "TESTS:")
    if process_resources:
        initialize_output_file(resources_output_path, "RESOURCES (CONFIG/DATA/DOCS):")

    # 4. Parallel Task Dispatch
    tasks = []

    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:
        for root, dirs, files in os.walk(input_path_abs):
            dirs[:] = [d for d in dirs if not matches_any(d, exclude_rx)]
            dirs.sort()
            files.sort()

            for file_name in files:
                if matches_any(file_name, exclude_rx) or not matches_include(file_name, include_rx):
                    results["skipped"] += 1
                    continue

                _, ext = os.path.splitext(file_name)
                if ext not in extensions and file_name not in extensions:
                    results["skipped"] += 1
                    continue

                file_path = os.path.join(root, file_name)
                rel_path = os.path.relpath(file_path, input_path_abs)

                tasks.append(executor.submit(
                    process_file_task,
                    file_path=file_path,
                    rel_path=rel_path,
                    ext=ext,
                    file_name=file_name,
                    process_modules=process_modules,
                    process_tests=process_tests,
                    process_resources=process_resources,
                    enable_sanitizer=enable_sanitizer,
                    mask_user_paths=mask_user_paths,
                    minify_output=minify_output,
                    locks=locks,
                    output_paths=output_paths
                ))

        for future in as_completed(tasks):
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

    # 5. Error Log Deployment
    actual_error_path = ""
    if save_error_log and results["errors"]:
        try:
            with open(error_output_path, "w", encoding="utf-8") as f:
                f.write("ERRORS:\n")
                for err_item in results["errors"]:
                    f.write("-" * 80 + "\n")
                    f.write(f"{err_item.rel_path}\n")
                    f.write(f"{err_item.error}\n")
            actual_error_path = error_output_path
        except OSError as e:
            logger.error(f"Failed to save error log: {e}")

    logger.info(f"Parallel Transcription finished. Processed: {results['processed']}. Errors: {len(results['errors'])}")

    return {
        "ok": True,
        "input_path": input_path_abs,
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