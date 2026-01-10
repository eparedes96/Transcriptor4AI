from __future__ import annotations

"""
Output formatting and transformation logic for Transcriptor4AI.

Handles the physical writing of file entries into consolidated documents,
applying a streaming transformation pipeline (Minify -> Sanitize -> Mask).
Refactored in V1.5.0 for high memory efficiency using line iterators.
"""

from typing import Iterator

from transcriptor4ai.utils.sanitizer import sanitize_text_stream, mask_local_paths_stream
from transcriptor4ai.utils.minify_code import minify_code_stream


# -----------------------------------------------------------------------------
# Output Formatting
# -----------------------------------------------------------------------------
def _append_entry(
        output_path: str,
        rel_path: str,
        line_iterator: Iterator[str],
        extension: str = "",
        enable_sanitizer: bool = False,
        mask_user_paths: bool = False,
        minify_output: bool = False,
) -> None:
    """
    Append a file content entry to the consolidated output file using streaming.

    This function chains multiple generators to process the file content
    without ever loading the full text into memory.

    Format:
    -------------------- (separator)
    <relative_path>
    <file_content>

    Args:
        output_path: Destination file path.
        rel_path: Relative path of the source file (header).
        line_iterator: Iterator yielding lines from the source file.
        extension: File extension for language-specific minification.
        enable_sanitizer: If True, redact secrets and keys.
        mask_user_paths: If True, replace local home paths with placeholders.
        minify_output: If True, remove comments and excessive whitespace.
    """
    # 1. Chain Transformation Pipeline (Lazy Evaluation)
    processed_stream = line_iterator

    if minify_output:
        processed_stream = minify_code_stream(processed_stream, extension)

    if enable_sanitizer:
        processed_stream = sanitize_text_stream(processed_stream)

    if mask_user_paths:
        processed_stream = mask_local_paths_stream(processed_stream)

    # 2. Final Formatting and Buffered Writing
    separator = "-" * 200

    try:
        with open(output_path, "a", encoding="utf-8") as out:
            out.write(f"{separator}\n")
            out.write(f"{rel_path}\n")

            for processed_line in processed_stream:
                out.write(processed_line)

            out.write("\n")

    except OSError as e:
        raise e