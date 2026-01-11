from __future__ import annotations

from typing import Iterator


def stream_file_content(file_path: str) -> Iterator[str]:
    """Read a file line by line using a generator."""
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line
