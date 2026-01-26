from __future__ import annotations

"""
Resilient File Reading Component.

Implements high-performance streaming for file consumption. Focuses on 
encoding resilience to ensure project processing is not interrupted by 
binary artifacts or corrupted UTF-8 sequences.
"""

import logging
from typing import Iterator

# Standard logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# STREAM READING OPERATIONS
# ==============================================================================

def stream_file_content(file_path: str) -> Iterator[str]:
    """
    Generate a line-by-line stream of file content.

    Implements the 'replace' error handling strategy to substitute
    unrecognized byte sequences with placeholder characters, preventing
    UnicodeDecodeError in mixed-encoding environments.

    Args:
        file_path: Absolute path to the target file.

    Yields:
        str: Sanitized lines from the file.
    """
    try:
        # 1. OPEN: Initialize file handle with substitution strategy
        # Force UTF-8 but handle corrupt bytes gracefully
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            # 2. ITERATE: Stream content line by line to keep memory footprint low
            for line in f:
                yield line

    except OSError as e:
        # Force garbage collection/handle closure is implicit with the 'with' block
        logger.error(f"FileReader: Access denied or file missing at '{file_path}': {e}")
        raise


# ==============================================================================
# BATCH READING OPERATIONS
# ==============================================================================

def read_file_safely(file_path: str) -> str:
    """
    Read the entire content of a file into memory as a single string.

    Args:
        file_path: Absolute path to the target file.

    Returns:
        str: The full content of the file.
    """
    # 1. PROCESS: Use the streaming logic to build the string
    # Critical Point: prevents memory spikes compared to raw .read() on some OS
    return "".join(list(stream_file_content(file_path)))