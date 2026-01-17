from __future__ import annotations

"""
Resilient File Reader.

Provides utilities to read files securely and resiliently, handling
encoding issues gracefully to prevent pipeline crashes.
"""

from typing import Iterator


def stream_file_content(file_path: str) -> Iterator[str]:
    """
    Read a file line by line using a generator.

    It uses 'errors="replace"' to handle non-UTF-8 files without crashing,
    inserting replacement characters for invalid bytes.

    Args:
        file_path: Absolute path to the file.

    Yields:
        str: Lines from the file.
    """
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line