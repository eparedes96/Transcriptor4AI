from __future__ import annotations

"""
Atomic Transcription Worker Service.

Orchestrates the sequential processing of individual file units within the 
pipeline. Manages the transformation lifecycle including AST-based 
skeletonization, code minification, and privacy-sensitive sanitization 
prior to thread-safe persistence.
"""

import logging
import threading
from typing import Any, Dict, Iterator, TYPE_CHECKING

# 1. LOCAL ANALYSIS & TRANSFORMATION
from transcriptor4ai.application.analysis.ast_parser import generate_skeleton_code
from transcriptor4ai.application.transformation.code_minifier import CodeMinifierService

# 2. PIPELINE COMPONENTS
from transcriptor4ai.application.pipeline.components.file_filters import determine_target_mode
from transcriptor4ai.application.pipeline.components.file_reader import stream_file_content
from transcriptor4ai.application.pipeline.components.file_writer import append_entry

# 3. TYPE CHECKING HINTS
if TYPE_CHECKING:
    from transcriptor4ai.application.transformation.privacy_sanitizer import PrivacySanitizerService

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# ATOMIC WORKER IMPLEMENTATION
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
        sanitizer_service: PrivacySanitizerService,
        composite_hash: str = ""
) -> Dict[str, Any]:
    """
    Execute the high-performance processing lifecycle for a single file unit.

    This function is designed for concurrent execution. It sequences
    extraction, transformation, and synchronized I/O.

    Args:
        file_path: Absolute filesystem source path.
        rel_path: Project-relative path used for context headers.
        ext: File extension for syntax-specific processing.
        file_name: Base filename for classification logic.
        processing_depth: Content detail level ('full', 'skeleton', 'tree_only').
        process_tests: Enable/Disable test suite targeting.
        process_resources: Enable/Disable non-code asset targeting.
        enable_sanitizer: Redact PII, IP addresses, and API Secrets.
        mask_user_paths: Anonymize local system paths in content.
        minify_output: Compress source code by stripping comments.
        locks: Mapping of thread locks to ensure atomic writes per category.
        output_paths: Physical destination paths for categorized artifacts.
        sanitizer_service: Pre-configured service for privacy redaction.
        composite_hash: Unique fingerprint for cache synchronization.

    Returns:
        Dict[str, Any]: Execution result containing success status and processed content.
    """

    # 1. CLASSIFY: Apply domain policy to categorize the target file
    target_mode = determine_target_mode(
        file_name, processing_depth, process_tests, process_resources
    )

    if target_mode == "skip":
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": "Filtered by processing mode",
            "mode": "skip"
        }

    try:
        # 2. EXTRACT: Acquire line-based source content stream
        raw_stream: Iterator[str] = stream_file_content(file_path)
        processed_stream: Iterator[str]

        # 3. TRANSFORM (Phase A): Structural Modification (Skeletonization)
        if processing_depth == "skeleton" and ext.lower() == ".py":
            # Materialization is required for AST analysis
            raw_content = "".join(list(raw_stream))
            skeleton_content = generate_skeleton_code(raw_content)
            processed_stream = iter([skeleton_content])
            logger.debug(f"Worker: Skeletonized Python source -> {rel_path}")
        else:
            processed_stream = raw_stream

        # 4. TRANSFORM (Phase B): Code Optimization (Minification)
        if minify_output:
            minifier = CodeMinifierService()
            processed_stream = minifier.minify_stream(processed_stream, ext)

        # 5. TRANSFORM (Phase C): Privacy Enforcement (Sanitization)
        if enable_sanitizer or mask_user_paths:
            if enable_sanitizer:
                processed_stream = sanitizer_service.sanitize_stream(processed_stream)
            if mask_user_paths:
                processed_stream = sanitizer_service.mask_paths_stream(processed_stream)

        # 6. MATERIALIZE: Compile stream for persistence and cache storage
        # Load processed results into memory for atomic write operation
        processed_content = "".join(list(processed_stream))

        # 7. PERSIST: Execute synchronized categorization
        lock = locks.get(target_mode)
        out_path = output_paths.get(target_mode)

        if not lock or not out_path:
            return {
                "ok": False,
                "rel_path": rel_path,
                "error": f"I/O Context missing for mode: {target_mode}",
                "mode": target_mode
            }

        with lock:
            append_entry(
                output_path=out_path,
                rel_path=rel_path,
                content=processed_content
            )

        # 8. COMPLETE: Return result metadata for engine aggregation
        return {
            "ok": True,
            "mode": target_mode,
            "rel_path": rel_path,
            "file_path": file_path,
            "processed_content": processed_content,
            "composite_hash": composite_hash
        }

    except (OSError, Exception) as e:
        logger.error(f"Worker: Critical failure processing {rel_path}: {e}")
        return {
            "ok": False,
            "rel_path": rel_path,
            "error": str(e),
            "mode": target_mode
        }