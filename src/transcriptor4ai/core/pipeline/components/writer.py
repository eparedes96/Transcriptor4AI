from __future__ import annotations

"""
Output Orchestration and Formatting.

Handles the physical persistence of the transcription entries. Manages 
the lazy-evaluation pipeline for code transformations (minification, 
masking, and sanitization) to maintain a low memory footprint.
"""

from typing import Iterator

from transcriptor4ai.core.processing.minifier import minify_code_stream
from transcriptor4ai.core.processing.sanitizer import sanitize_text_stream, mask_local_paths_stream

# -----------------------------------------------------------------------------
# FILE OUTPUT MANAGEMENT
# -----------------------------------------------------------------------------

def append_entry(
        output_path: str,
        rel_path: str,
        line_iterator: Iterator[str],
        extension: str = "",
        enable_sanitizer: bool = False,
        mask_user_paths: bool = False,
        minify_output: bool = False,
) -> None:
    """
    Append a processed file entry to a consolidated text file.

    Chains multiple transformation generators to the input stream.
    Transformations are applied on-the-fly as the lines are written,
    ensuring that large files do not exhaust system memory.

    Output Format:
    -------------------- (200 char separator)
    <relative_path_header>
    <processed_content>

    Args:
        output_path: Target consolidated file.
        rel_path: Source file identifier (header).
        line_iterator: Source content generator.
        extension: File extension for syntax-aware minification.
        enable_sanitizer: Redact sensitive keys and network info.
        mask_user_paths: Anonymize local environment paths.
        minify_output: Strip non-essential code characters.

    Raises:
        OSError: If filesystem write permissions are denied.
    """
    # 1. Pipeline Assembly (Lazy Transformation Chain)
    processed_stream = line_iterator

    if minify_output:
        processed_stream = minify_code_stream(processed_stream, extension)

    if enable_sanitizer:
        processed_stream = sanitize_text_stream(processed_stream)

    if mask_user_paths:
        processed_stream = mask_local_paths_stream(processed_stream)

    # 2. Synchronous Disk Persistence
    separator = "-" * 200

    try:
        with open(output_path, "a", encoding="utf-8") as out:
            out.write(f"{separator}\n")
            out.write(f"{rel_path}\n")

            # Iterate through the chained generator and write directly
            for processed_line in processed_stream:
                out.write(processed_line)

            # Ensure separation between entries
            out.write("\n")

    except OSError as e:
        # Propagate error to worker/manager level
        raise e


def initialize_output_file(file_path: str, header: str) -> None:
    """
    Perform a clean initialization of an output file.

    Creates or overwrites the file with a descriptive header to
    set the context for the transcription content.

    Args:
        file_path: Target file path.
        header: Introductory text for the file.
    """
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(f"{header}\n")