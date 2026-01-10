from __future__ import annotations

"""
Output formatting and transformation logic for Transcriptor4AI.

Handles the physical writing of file entries into consolidated documents,
applying minification and sanitization filters if configured.
"""

from transcriptor4ai.utils.sanitizer import sanitize_text, mask_local_paths
from transcriptor4ai.utils.minify_code import minify_code


# -----------------------------------------------------------------------------
# Output Formatting
# -----------------------------------------------------------------------------
def _append_entry(
        output_path: str,
        rel_path: str,
        content: str,
        extension: str = "",
        enable_sanitizer: bool = False,
        mask_user_paths: bool = False,
        minify_output: bool = False,
) -> None:
    """
    Append a file content entry to the consolidated output file.
    Applies a transformation pipeline: Minify -> Sanitize -> Mask Paths.

    Format:
    -------------------- (separator)
    <relative_path>
    <file_content>

    Args:
        output_path: Destination file path.
        rel_path: Relative path of the source file (header).
        content: The actual content of the source file.
        extension: File extension for language-specific minification.
        enable_sanitizer: If True, redact secrets and keys.
        mask_user_paths: If True, replace local home paths with placeholders.
        minify_output: If True, remove comments and excessive whitespace.
    """
    # 1. Pipeline Transformation
    processed_content = content

    if minify_output:
        processed_content = minify_code(processed_content, extension)

    if enable_sanitizer:
        processed_content = sanitize_text(processed_content)

    if mask_user_paths:
        processed_content = mask_local_paths(processed_content)

    # 2. Final Formatting
    separator = "-" * 200

    with open(output_path, "a", encoding="utf-8") as out:
        out.write(f"{separator}\n")
        out.write(f"{rel_path}\n")
        out.write(processed_content.rstrip("\n") + "\n")