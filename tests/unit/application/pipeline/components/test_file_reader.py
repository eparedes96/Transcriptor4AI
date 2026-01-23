from __future__ import annotations

"""
Unit tests for the File Reader service.

Verifies:
1. Correct streaming of file content.
2. Resilience against encoding errors (Binary/Corrupt files).
"""

import pytest

from transcriptor4ai.core.pipeline.components.reader import stream_file_content


def test_stream_file_content_normal(tmp_path):
    """Verify reading a standard UTF-8 file."""
    f = tmp_path / "normal.txt"
    content = "Line 1\nLine 2\nLine 3"
    f.write_text(content, encoding="utf-8")

    iterator = stream_file_content(str(f))
    lines = list(iterator)

    assert len(lines) == 3
    assert lines[0] == "Line 1\n"


def test_stream_file_content_resilience_to_binary(tmp_path):
    """
    CRITICAL: Verify that reading a non-UTF-8 (binary) file does NOT raise
    UnicodeDecodeError. It should replace invalid bytes.
    """
    f = tmp_path / "corrupt.py"
    # Write invalid UTF-8 bytes (0x80 is not valid start byte)
    f.write_bytes(b"print('Hello')\n\x80\x81\xff\nprint('End')")

    iterator = stream_file_content(str(f))

    try:
        lines = list(iterator)
    except UnicodeDecodeError:
        pytest.fail("Reader crashed on invalid encoding! It must use errors='replace'.")

    # Verify content structure is preserved even with replacements
    assert "print('Hello')\n" in lines[0]
    assert "\ufffd" in lines[1]
    assert "print('End')" in lines[2]


def test_stream_file_content_handles_empty(tmp_path):
    """Verify empty file handling."""
    f = tmp_path / "empty.txt"
    f.write_text("", encoding="utf-8")

    lines = list(stream_file_content(str(f)))
    assert lines == []


def test_stream_file_raises_os_error_on_missing():
    """
    The reader should let OSError propagate up to the worker,
    which handles the error reporting.
    """
    with pytest.raises(OSError):
        list(stream_file_content("/non/existent/path"))