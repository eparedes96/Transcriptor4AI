from __future__ import annotations

"""
Source code transcription service.

Recursively scans directories and consolidates files into text documents 
based on processing modes and filters. Implements lazy writing to prevent 
the creation of empty files.
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
        mode: str = "all",
        extensions: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        output_prefix: str = "transcription",
        output_folder: str = ".",
        save_error_log: bool = True,
) -> Dict[str, Any]:
    """
    Consolidate source code into text files based on filtering criteria.

    Implements lazy writing: files are only created if content is found.

    Args:
        input_path: Source directory to scan.
        mode: "all", "modules_only", "tests_only".
        extensions: List of file extensions to process.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        output_prefix: Prefix for output files.
        output_folder: Destination directory.
        save_error_log: Whether to write a separate error log file (only if errors occur).

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
    output_folder_abs = os.path.abspath(output_folder)

    include_rx = compile_patterns(include_patterns)
    exclude_rx = compile_patterns(exclude_patterns)

    generate_tests = (mode == "tests_only" or mode == "all")
    generate_modules = (mode == "modules_only" or mode == "all")

    # -------------------------
    # Prepare Output Directory
    # -------------------------
    ok, err = _safe_mkdir(output_folder_abs)
    if not ok:
        logger.error(f"Failed to create output directory: {err}")
        return {
            "ok": False,
            "error": f"Output directory error '{output_folder_abs}': {err}",
            "output_folder": output_folder_abs,
        }

    path_tests = os.path.join(output_folder_abs, f"{output_prefix}_tests.txt")
    path_modules = os.path.join(output_folder_abs, f"{output_prefix}_modules.txt")
    path_errors = os.path.join(output_folder_abs, f"{output_prefix}_errors.txt")

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

            is_test_file = is_test(file_name)
            if mode == "tests_only" and not is_test_file:
                skipped_count += 1
                continue
            if mode == "modules_only" and is_test_file:
                skipped_count += 1
                continue

            # --- Processing ---
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
                if is_test_file and generate_tests:
                    if not tests_file_initialized:
                        _initialize_output_file(path_tests, "CODE:")
                        tests_file_initialized = True
                    _append_entry(path_tests, rel_path, content)
                    tests_written += 1

                if (not is_test_file) and generate_modules:
                    if not modules_file_initialized:
                        _initialize_output_file(path_modules, "CODE:")
                        modules_file_initialized = True
                    _append_entry(path_modules, rel_path, content)
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
            with open(path_errors, "w", encoding="utf-8") as f:
                f.write("ERRORS:\n")
                for err_item in errors:
                    f.write("-" * 80 + "\n")
                    f.write(f"{err_item.rel_path}\n")
                    f.write(f"{err_item.error}\n")
            actual_error_path = path_errors
            logger.info(f"Error log saved to: {path_errors}")
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
        "output_folder": output_folder_abs,
        "mode": mode,
        "generated": {
            "tests": path_tests if tests_file_initialized else "",
            "modules": path_modules if modules_file_initialized else "",
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