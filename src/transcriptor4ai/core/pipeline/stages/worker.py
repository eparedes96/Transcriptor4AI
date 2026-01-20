from __future__ import annotations

"""
Atomic Transcription Worker.

Encapsulates the processing logic for a single file unit. Handles classification
(logic vs. test vs. resource), stream initialization, and concurrent write
delegation while respecting thread synchronization locks. 
Implements 'processing_depth' routing to support Skeleton Mode
via AST-based transformation for Python files.
"""

import logging
import threading
from typing import Any, Dict, Iterator

from transcriptor4ai.core.analysis.ast_parser import generate_skeleton_code
from transcriptor4ai.core.pipeline.components.filters import is_resource_file, is_test
from transcriptor4ai.core.pipeline.components.reader import stream_file_content
from transcriptor4ai.core.processing.minifier import minify_code_stream
from transcriptor4ai.core.processing.sanitizer import (
    mask_local_paths_stream,
    sanitize_text_stream,
)

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def process_file_task(
        file_path: str,
        rel_path: str,
        ext: str,
        file_name: str,
        processing_depth: str,
        process_tests: bool,
        process_resources: bool,
        enable_sanitizer: bool,
        mask_user_paths: bool,
        minify_output: bool,
        locks: Dict[str, threading.Lock],
        output_paths: Dict[str, str],
        composite_hash: str = ""
) -> Dict[str, Any]:
    """
    Execute the full processing lifecycle for a single file.

    This function is designed to be executed within a ThreadPoolExecutor.
    It classifies the file, applies AST transformations if 'skeleton' depth
    is requested, executes sanitization/minification, and appends the content
    to the appropriate consolidated file.

    Args:
        file_path: Absolute filesystem path.
        rel_path: Relative path for header identification.
        ext: File extension (including dot).
        file_name: Base name of the file.
        processing_depth: Content depth strategy ("full", "skeleton", "tree_only").
        process_tests: Flag to enable test suite transcription.
        process_resources: Flag to enable resource transcription.
        enable_sanitizer: Flag for PII redaction.
        mask_user_paths: Flag for environment anonymization.
        minify_output: Flag for code minification.
        locks: Thread synchronization locks for shared output files.
        output_paths: Target paths for different transcription categories.
        composite_hash: Unique identifier for cache tracking (optional).

    Returns:
        Dict[str, Any]: Task result status, including target mode, error details,
                        and the processed content for caching.
    """

    # 1. Classification Phase
    file_is_test = is_test(file_name)
    file_is_resource = is_resource_file(file_name)
    target_mode = "skip"

    # Determine processing category based on file type and config flags
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

    # Early exit if the file does not match active processing modes
    if target_mode == "skip":
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": "Filtered by mode or depth",
            "mode": "skip"
        }

    # 2. Transcription Phase
    try:
        # Initial Content Acquisition
        raw_stream: Iterator[str] = stream_file_content(file_path)
        processed_stream: Iterator[str]

        # If Skeleton Mode is requested and file is Python, we must materialize
        if processing_depth == "skeleton" and ext.lower() == ".py":
            raw_content = "".join(list(raw_stream))
            skeleton_content = generate_skeleton_code(raw_content)
            # Convert back to iterator to maintain pipeline homogeneity
            processed_stream = iter([skeleton_content])
            logger.debug(f"Skeletonized: {rel_path}")
        else:
            processed_stream = raw_stream

        # 3. Content Transformation Pipeline
        if minify_output:
            processed_stream = minify_code_stream(processed_stream, ext)

        if enable_sanitizer:
            processed_stream = sanitize_text_stream(processed_stream)

        if mask_user_paths:
            processed_stream = mask_local_paths_stream(processed_stream)

        # Materialize stream to string for cache compatibility and atomic writing
        processed_content = "".join(list(processed_stream))

        # 4. Persistence Phase (Thread-Safe)
        lock = locks.get(target_mode)
        if not lock:
            return {
                "ok": False,
                "rel_path": rel_path,
                "error": f"No thread lock found for mode: {target_mode}",
                "mode": target_mode
            }

        output_path = output_paths.get(target_mode)
        if not output_path:
            return {
                "ok": False,
                "rel_path": rel_path,
                "error": f"No output path found for mode: {target_mode}",
                "mode": target_mode
            }

        # Write to disk under thread lock to prevent interleaved content
        separator = "-" * 200
        with lock:
            with open(output_path, "a", encoding="utf-8") as out:
                out.write(f"{separator}\n")
                out.write(f"{rel_path}\n")
                out.write(processed_content)
                out.write("\n")

        return {
            "ok": True,
            "mode": target_mode,
            "rel_path": rel_path,
            "file_path": file_path,
            "processed_content": processed_content,
            "composite_hash": composite_hash
        }

    except (OSError, UnicodeDecodeError) as e:
        # Capture I/O or encoding errors without crashing the executor
        logger.error(f"Worker failed for {rel_path}: {e}")
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": str(e),
            "mode": target_mode
        }