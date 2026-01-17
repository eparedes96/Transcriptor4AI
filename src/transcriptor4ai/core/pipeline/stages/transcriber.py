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
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.core.pipeline.components.filters import (
    compile_patterns,
    default_extensions,
    default_exclude_patterns,
    default_include_patterns,
    load_gitignore_patterns,
    matches_any,
    matches_include,
    is_resource_file,
    is_test
)
from transcriptor4ai.core.pipeline.stages.worker import process_file_task
from transcriptor4ai.core.pipeline.components.writer import initialize_output_file
from transcriptor4ai.domain.transcription_models import TranscriptionError
from transcriptor4ai.infra.fs import safe_mkdir

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

    # 1. Preparar parámetros y reglas de filtrado
    include_rx, exclude_rx = _prepare_filtering_rules(
        input_path, include_patterns, exclude_patterns, respect_gitignore
    )

    # 2. Inicializar archivos y entorno de hilos
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

    # 3. Ejecutar escaneo y procesamiento en paralelo
    _execute_parallel_transcription(
        input_path, extensions or default_extensions(), include_rx, exclude_rx,
        process_modules, process_tests, process_resources,
        enable_sanitizer, mask_user_paths, minify_output,
        locks, output_paths, results
    )

    # 4. Finalizar reportes y construir respuesta
    actual_error_path = _finalize_error_reporting(
        save_error_log, error_output_path, results["errors"]
    )

    logger.info(f"Parallel Transcription finished. Processed: {results['processed']}. Errors: {len(results['errors'])}")

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


# -----------------------------------------------------------------------------
# HELPERS PRIVADOS DE TRANSCRIPCIÓN
# -----------------------------------------------------------------------------

def _prepare_filtering_rules(
        input_path: str,
        include_patterns: Optional[List[str]],
        exclude_patterns: Optional[List[str]],
        respect_gitignore: bool
) -> Tuple[List[Any], List[Any]]:
    """Compile and merge all inclusion/exclusion regex patterns."""
    input_path_abs = os.path.abspath(input_path)

    final_includes = include_patterns if include_patterns is not None else default_include_patterns()
    final_exclusions = list(exclude_patterns) if exclude_patterns is not None else default_exclude_patterns()

    if respect_gitignore:
        git_patterns = load_gitignore_patterns(input_path_abs)
        if git_patterns:
            logger.debug(f"Loaded {len(git_patterns)} patterns from .gitignore")
            final_exclusions.extend(git_patterns)

    return compile_patterns(final_includes), compile_patterns(final_exclusions)


def _initialize_execution_environment(
        modules_path: str,
        tests_path: str,
        resources_path: str,
        error_path: str,
        process_modules: bool,
        process_tests: bool,
        process_resources: bool
) -> Tuple[Dict[str, threading.Lock], Dict[str, str]]:
    """Prepare output directories, initialize files and create thread locks."""
    for p in [modules_path, tests_path, resources_path, error_path]:
        safe_mkdir(os.path.dirname(os.path.abspath(p)))

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
        results: Dict[str, Any]
) -> None:
    """Walk the filesystem and dispatch tasks to the thread pool."""
    input_path_abs = os.path.abspath(input_path)
    tasks = []

    with ThreadPoolExecutor(thread_name_prefix="TranscriptionWorker") as executor:
        for root, dirs, files in os.walk(input_path_abs):
            dirs[:] = [d for d in dirs if not matches_any(d, exclude_rx)]
            dirs.sort()
            files.sort()

            for file_name in files:
                if matches_any(file_name, exclude_rx):
                    results["skipped"] += 1
                    continue

                if not matches_include(file_name, include_rx):
                    results["skipped"] += 1
                    continue

                _, ext = os.path.splitext(file_name)
                should_process = False

                if process_resources and is_resource_file(file_name):
                    should_process = True
                elif process_tests and is_test(file_name):
                    should_process = True
                elif process_modules:
                    if ext in extensions or file_name in extensions:
                        should_process = True

                if not should_process:
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


def _finalize_error_reporting(
        save_error_log: bool,
        error_output_path: str,
        errors: List[TranscriptionError]
) -> str:
    """Write the error log file if necessary and return its path."""
    actual_error_path = ""
    if save_error_log and errors:
        try:
            with open(error_output_path, "w", encoding="utf-8") as f:
                f.write("ERRORS:\n")
                for err_item in errors:
                    f.write("-" * 80 + "\n")
                    f.write(f"{err_item.rel_path}\n")
                    f.write(f"{err_item.error}\n")
            actual_error_path = error_output_path
        except OSError as e:
            logger.error(f"Failed to save error log: {e}")
    return actual_error_path