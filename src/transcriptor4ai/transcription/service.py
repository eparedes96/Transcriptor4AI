from __future__ import annotations

"""
Source code transcription service.

Recursively scans directories and consolidates files into text documents 
based on granular processing flags and filters. Implements lazy writing 
to prevent the creation of empty files.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from transcriptor4ai.filtering import (
    compile_patterns,
    default_extensions,
    default_exclude_patterns,
    default_include_patterns,
    is_test,
    matches_any,
    matches_include,
)
from transcriptor4ai.paths import _safe_mkdir
from transcriptor4ai.transcription.format import _append_entry
from transcriptor4ai.transcription.models import TranscriptionError

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def transcribe_code(
        input_path: str,
        modules_output_path: str,
        tests_output_path: str,
        error_output_path: str,
        process_modules: bool = True,
        process_tests: bool = True,
        extensions: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        save_error_log: bool = True,
) -> Dict[str, Any]:
    """
    Consolidate source code into specific text files based on filtering criteria.

    This function is output-path agnostic; it writes to whatever paths are provided
    (temporary or final) if the corresponding 'process_' flag is True.

    Args:
        input_path: Source directory to scan.
        modules_output_path: Destination path for source code (scripts).
        tests_output_path: Destination path for test code.
        error_output_path: Destination path for error log.
        process_modules: If True, extract non-test files.
        process_tests: If True, extract test files.
        extensions: List of file extensions to process.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        save_error_log: Whether to write the error log file (only if errors occur).

    Returns:
        A dictionary containing counters, paths, and status.
    """
    logger.info(f"Starting transcription scan in: {input_path}")

    # -------------------------
    # Input Normalization
    # -------------------------
    if extensions is None:
        extensions = default_extensions()
    if include_patterns is None:
        include_patterns = default_include_patterns()
    if exclude_patterns is None:
        exclude_patterns = default_exclude_patterns()

    input_path_abs = os.path.abspath(input_path)

    for p in [modules_output_path, tests_output_path, error_output_path]:
        _safe_mkdir(os.path.dirname(os.path.abspath(p)))

    include_rx = compile_patterns(include_patterns)
    exclude_rx = compile_patterns(exclude_patterns)

    # -------------------------
    # Filesystem Traversal
    # -------------------------
    errors: List[TranscriptionError] = []
    processed_count = 0
    skipped_count = 0
    tests_written = 0
    modules_written = 0

    # Lazy initialization flags
    tests_file_initialized = False
    modules_file_initialized = False

    for root, dirs, files in os.walk(input_path_abs):
        dirs[:] = [d for d in dirs if not matches_any(d, exclude_rx)]
        dirs.sort()
        files.sort()

        for file_name in files:
            _, ext = os.path.splitext(file_name)

            # --- Filtering ---
            if ext not in extensions:
                skipped_count += 1
                continue

            if matches_any(file_name, exclude_rx):
                skipped_count += 1
                continue
            if not matches_include(file_name, include_rx):
                skipped_count += 1
                continue

            # --- Classification ---
            is_test_file = is_test(file_name)

            should_process = False
            if is_test_file and process_tests:
                should_process = True
            elif (not is_test_file) and process_modules:
                should_process = True

            if not should_process:
                skipped_count += 1
                continue

            # --- Extraction & Writing ---
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, input_path_abs)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Error reading file {rel_path}: {e}")
                errors.append(TranscriptionError(rel_path=rel_path, error=str(e)))
                continue

            try:
                # Write to Tests File
                if is_test_file:
                    if not tests_file_initialized:
                        _initialize_output_file(tests_output_path, "TESTS:")
                        tests_file_initialized = True
                    _append_entry(tests_output_path, rel_path, content)
                    tests_written += 1

                # Write to Modules (Scripts) File
                else:
                    if not modules_file_initialized:
                        _initialize_output_file(modules_output_path, "SCRIPTS:")
                        modules_file_initialized = True
                    _append_entry(modules_output_path, rel_path, content)
                    modules_written += 1

                processed_count += 1
                logger.debug(f"Processed: {rel_path}")

            except OSError as e:
                msg = f"Error writing to output: {e}"
                logger.error(msg)
                errors.append(TranscriptionError(rel_path=rel_path, error=msg))
                continue

    # -------------------------
    # Lazy Error Logging
    # -------------------------
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
            logger.info(f"Error log saved to: {error_output_path}")
        except OSError as e:
            logger.error(f"Failed to save error log: {e}")

    logger.info(
        f"Transcription finished. Processed: {processed_count}, "
        f"Tests: {tests_written}, Modules: {modules_written}, Errors: {len(errors)}"
    )

    # -------------------------
    # Result Construction
    # -------------------------
    return {
        "ok": True,
        "input_path": input_path_abs,
        "process_modules": process_modules,
        "process_tests": process_tests,
        "generated": {
            "tests": tests_output_path if tests_file_initialized else "",
            "modules": modules_output_path if modules_file_initialized else "",
            "errors": actual_error_path,
        },
        "counters": {
            "processed": processed_count,
            "skipped": skipped_count,
            "tests_written": tests_written,
            "modules_written": modules_written,
            "errors": len(errors),
        },
    }


# -----------------------------------------------------------------------------
# Private Helpers
# -----------------------------------------------------------------------------
def _initialize_output_file(file_path: str, header: str) -> None:
    """Create a file and write the initial header."""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{header}\n")