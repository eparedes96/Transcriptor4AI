from __future__ import annotations

"""
Atomic Transcription Worker.

Encapsulates the processing logic for a single file unit. Orchestrates 
content extraction, AST skeletonization, code minification, and security 
sanitization in a memory-efficient streaming pipeline.
"""

import logging
import threading
from typing import Any, Dict, Iterator

# Analysis & Transformation Services
from transcriptor4ai.application.analysis.ast_parser import generate_skeleton_code
from transcriptor4ai.application.transformation.code_minifier import CodeMinifierService

# Pipeline Components
from transcriptor4ai.application.pipeline.components.file_reader import stream_file_content
from transcriptor4ai.application.pipeline.components.file_writer import append_entry
from transcriptor4ai.application.pipeline.components.file_filters import determine_target_mode

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# WORKER: ATOMIC FILE PROCESSING
# ==============================================================================

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
    Execute the full processing lifecycle for a single file unit.

    Designed to run within a ThreadPoolExecutor. It coordinates extraction,
    transformation, and thread-safe persistence.

    Args:
        file_path: Absolute filesystem path.
        rel_path: Project-relative path for identification.
        ext: File extension.
        file_name: Base filename.
        processing_depth: Content depth strategy ("full", "skeleton", "tree_only").
        process_tests: Enable/Disable test suite processing.
        process_resources: Enable/Disable resource processing.
        enable_sanitizer: Redact PII and Secrets.
        mask_user_paths: Anonymize local system paths.
        minify_output: Strip comments and white-space.
        locks: Thread synchronization locks map.
        output_paths: Destination paths map.
        composite_hash: Fingerprint for cache tracking.

    Returns:
        Dict[str, Any]: Task result metadata and processed content.
    """

    # 1. CLASSIFY: Determine target category via externalized domain policy
    target_mode = determine_target_mode(
        file_name, processing_depth, process_tests, process_resources
    )

    if target_mode == "skip":
        return {"ok": False, "rel_path": rel_path, "error": "Filtered by mode", "mode": "skip"}

    try:
        # 2. EXTRACT: Acquire source content stream
        raw_stream: Iterator[str] = stream_file_content(file_path)
        processed_stream: Iterator[str]

        # 3. TRANSFORM: Apply specialized processing chain

        # 3.1 Skeletonization: Requires materialization if Python file
        if processing_depth == "skeleton" and ext.lower() == ".py":
            raw_content = "".join(list(raw_stream))
            skeleton_content = generate_skeleton_code(raw_content)
            processed_stream = iter([skeleton_content])
            logger.debug(f"Worker: Skeletonized {rel_path}")
        else:
            processed_stream = raw_stream

        # 3.2 Optimization: Minification Service
        if minify_output:
            minifier = CodeMinifierService()
            processed_stream = minifier.minify_stream(processed_stream, ext)

        # 3.3 Security: Sanitizer Service
        if enable_sanitizer or mask_user_paths:
            # Note: Implementation expects these to be injected or available via shim
            from transcriptor4ai.application.transformation.privacy_sanitizer import _get_default_service
            sanitizer = _get_default_service()

            if enable_sanitizer:
                processed_stream = sanitizer.sanitize_stream(processed_stream)
            if mask_user_paths:
                processed_stream = sanitizer.mask_paths_stream(processed_stream)

        # 4. MATERIALIZE: Join stream for atomic persistence and cache storage
        processed_content = "".join(list(processed_stream))

        # 5. PERSIST: Delegate thread-safe writing to the specialized component
        lock = locks.get(target_mode)
        out_path = output_paths.get(target_mode)

        if not lock or not out_path:
            return {"ok": False, "rel_path": rel_path, "error": "Missing I/O context", "mode": target_mode}

        with lock:
            append_entry(
                output_path=out_path,
                rel_path=rel_path,
                content=processed_content
            )

        return {
            "ok": True,
            "mode": target_mode,
            "rel_path": rel_path,
            "file_path": file_path,
            "processed_content": processed_content,
            "composite_hash": composite_hash
        }

    except (OSError, Exception) as e:
        logger.error(f"Worker: Failed to process {rel_path}: {e}")
        return {"ok": False, "rel_path": rel_path, "error": str(e), "mode": target_mode}