from __future__ import annotations

"""
Pipeline Output Persistence Component.

Responsible for the physical writing and visual formatting of transcription 
artifacts. It ensures a consistent look-and-feel across all output files by 
standardizing headers, separators, and atomic entry appending.
"""

import logging
from typing import Final

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# VISUAL FORMATTING CONSTANTS
# ==============================================================================

# Standard separator used to distinguish between different file entries
_ENTRY_SEPARATOR: Final[str] = "-" * 200


# ==============================================================================
# PUBLIC WRITING API
# ==============================================================================

def append_entry(
        output_path: str,
        rel_path: str,
        content: str
) -> None:
    """
    Append a processed entry to a consolidated text file with standard formatting.

    This function expects 'content' to be already transformed (sanitized,
    minified, etc.). It applies the visual block structure required for
    LLM context clarity.

    Format:
    -------------------- (Separator)
    <relative_path>
    <processed_content>

    Args:
        output_path: Absolute path to the destination .txt file.
        rel_path: Relative identifier of the source file for the header.
        content: The final string content to persist.

    Raises:
        OSError: If the filesystem denies write access.
    """
    # 1. FORMAT: Construct the visual block
    # We use a leading newline to ensure separation from the previous block
    entry_block = (
        f"{_ENTRY_SEPARATOR}\n"
        f"{rel_path}\n"
        f"{content}\n"
    )

    # 2. PERSIST: Atomic-like append operation
    try:
        with open(output_path, "a", encoding="utf-8") as out:
            out.write(entry_block)

    except OSError as e:
        logger.error(f"FileWriter: Failed to append entry for {rel_path}: {e}")
        raise


def initialize_output_file(file_path: str, header: str) -> None:
    """
    Perform a clean initialization of an output file with a section header.

    Args:
        file_path: Destination file path (will be overwritten).
        header: Descriptive text to identify the category (e.g., 'TESTS:').
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"{header}\n")

    except OSError as e:
        logger.error(f"FileWriter: Failed to initialize {file_path}: {e}")
        raise


# ==============================================================================
# CACHE-SPECIFIC WRITERS
# ==============================================================================

def append_cache_entry(
        output_path: str,
        rel_path: str,
        content: str
) -> None:
    """
    Technical wrapper for writing cache hits.

    Maintains semantic parity with the normal 'append_entry' but allows
    future differentiation in formatting if cache hits need specific markers.
    """
    append_entry(output_path, rel_path, content)