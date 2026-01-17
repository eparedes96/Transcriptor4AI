from __future__ import annotations

"""
Atomic Transcription Worker.

This module contains the logic for processing a single file in isolation.
It handles classification, filtering, reading, and delegating the write
operation to the writer module.
"""

import threading
from typing import Dict, Any

from transcriptor4ai.core.pipeline.components.filters import is_test, is_resource_file
from transcriptor4ai.core.pipeline.components.reader import stream_file_content
from transcriptor4ai.core.pipeline.components.writer import append_entry


def process_file_task(
        file_path: str,
        rel_path: str,
        ext: str,
        file_name: str,
        process_modules: bool,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str]
) -> Dict[str, Any]:
    """
    Process a single file: Classify, Read, Transform, and Write.

    This function is designed to run inside a thread worker. It respects
    global locks to ensure thread-safe writing to shared output files.

    Args:
        file_path: Absolute path to the source file.
        rel_path: Relative path for display purposes.
        ext: File extension (e.g., '.py').
        file_name: Base name of the file.
        process_modules: Flag to process source modules.
        process_tests: Flag to process test files.
        process_resources: Flag to process resource files.
        enable_sanitizer: Flag to enable redaction.
        mask_user_paths: Flag to enable path masking.
        minify_output: Flag to enable code minification.
        locks: Dictionary of threading locks for output files.
        output_paths: Dictionary mapping modes to output file paths.

    Returns:
        Dict[str, Any]: Result dictionary with 'ok', 'mode', and 'error' keys.
    """
    # 1. Classification
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    if file_is_test:
        if process_tests:
            target_mode = "test"
    elif file_is_resource:
        if process_resources:
            target_mode = "resource"
        elif process_modules:
            target_mode = "module"
    else:
        if process_modules:
            target_mode = "module"

    if target_mode == "skip":
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": "Filtered by mode",
            "mode": "skip"
        }

    # 2. Transcription Logic
    try:
        line_iterator = stream_file_content(file_path)

        lock = locks.get(target_mode)
        if not lock:
            return {
                "ok": False,
                "rel_path": rel_path,
                "error": f"No lock found for mode {target_mode}",
                "mode": target_mode
            }

        with lock:
            append_entry(
                output_path=output_paths[target_mode],
                rel_path=rel_path,
                line_iterator=line_iterator,
                extension=ext,
                enable_sanitizer=enable_sanitizer,
                mask_user_paths=mask_user_paths,
                minify_output=minify_output
            )
        return {"ok": True, "mode": target_mode, "rel_path": rel_path}

    except (OSError, UnicodeDecodeError) as e:
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": str(e),
            "mode": target_mode
        }