from __future__ import annotations

"""
Resilient File Reading Component.

Implements high-performance streaming for file consumption. Focuses on 
encoding resilience to ensure project processing is not interrupted by 
binary artifacts or corrupted UTF-8 sequences.
"""

from typing import Iterator

# -----------------------------------------------------------------------------
# STREAM READING OPERATIONS
# -----------------------------------------------------------------------------

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
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line