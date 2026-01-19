from __future__ import annotations

"""
Atomic Transcription Worker.

Encapsulates the processing logic for a single file unit. Handles classification 
(logic vs. test vs. resource), stream initialization, and concurrent write 
delegation while respecting thread synchronization locks.
"""

import threading
from typing import Any, Dict

from transcriptor4ai.core.pipeline.components.filters import is_resource_file, is_test
from transcriptor4ai.core.pipeline.components.reader import stream_file_content
from transcriptor4ai.core.pipeline.components.writer import append_entry

# -----------------------------------------------------------------------------
# TASK EXECUTION LOGIC
# -----------------------------------------------------------------------------

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
    Execute the full processing lifecycle for a single file.

    This function is designed to be executed within a ThreadPoolExecutor.
    It classifies the file, opens a resilient stream, and appends the
    transformed content to the appropriate consolidated file using locks.

    Args:
        file_path: Absolute filesystem path.
        rel_path: Relative path for header identification.
        ext: File extension.
        file_name: Base name of the file.
        process_modules: Flag to enable logic module transcription.
        process_tests: Flag to enable test suite transcription.
        process_resources: Flag to enable resource transcription.
        enable_sanitizer: Flag for PII redaction.
        mask_user_paths: Flag for environment anonymization.
        minify_output: Flag for code minification.
        locks: Thread synchronization locks for shared output files.
        output_paths: Target paths for different transcription categories.

    Returns:
        Dict[str, Any]: Task result status, including target mode and error details.
    """
    # 1. Classification Phase
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    # Determine processing category based on file type and config flags
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

    # Early exit if the file does not match active processing modes
    if target_mode == "skip":
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": "Filtered by mode",
            "mode": "skip"
        }

    # 2. Transcription Phase
    try:
        # Initialize resilient stream reader
        line_iterator = stream_file_content(file_path)

        # Retrieve the synchronization lock for the target file
        lock = locks.get(target_mode)
        if not lock:
            return {
                "ok": False,
                "rel_path": rel_path,
                "error": f"No thread lock found for mode: {target_mode}",
                "mode": target_mode
            }

        # Thread-safe write operation
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
        # Capture I/O or encoding errors without crashing the executor
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": str(e),
            "mode": target_mode
        }