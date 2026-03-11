from __future__ import annotations

from pathlib import Path

import pytest

from transcriptor4ai.application.pipeline.components.file_reader import (
    read_file_safely,
    stream_file_content,
)
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

# ==============================================================================
# TEST GROUP: FILE ENCODING AND BINARY RESILIENCE
# ==============================================================================

@pytest.fixture
def fs() -> FileSystemAdapter:
    """Provides a real instance of the FileSystemAdapter."""
    return FileSystemAdapter()

@pytest.mark.integration
def test_read_file_content_resists_pure_binary_files(fs, tmp_path: Path):
    """
    Ensures that reading a completely binary/corrupted file does not raise
    a UnicodeDecodeError and safely replaces invalid bytes.
    """
    # 1. ARRANGE: Create a file with pure binary/invalid UTF-8 bytes
    binary_file = tmp_path / "corrupted.bin"
    # \x80 and \xff are invalid start bytes in UTF-8
    bad_bytes = b"header\x80\xff\xfe\x00footer"
    binary_file.write_bytes(bad_bytes)

    # 2. ACT: Attempt to read the file content
    content = fs.read_file_content(str(binary_file))

    # 3. ASSERT: Process did not crash, and replacement characters () were injected
    assert "header" in content
    assert "footer" in content
    assert "\ufffd" in content  # \ufffd is the standard Unicode replacement character ()

@pytest.mark.integration
def test_read_file_content_resists_legacy_encodings(fs, tmp_path: Path):
    """
    Validates resilience against files saved in legacy encodings (e.g., ISO-8859-1)
    that contain special characters which break strict UTF-8 decoders.
    """
    # 1. ARRANGE: Create a file encoded in latin-1 instead of utf-8
    legacy_file = tmp_path / "legacy_windows.txt"
    spanish_text = "Año de creación: 2026. ¡Éxito!"
    # Encode explicitly as latin-1. Reading this as utf-8 normally crashes.
    legacy_file.write_bytes(spanish_text.encode("latin-1"))

    # 2. ACT: Read via the system adapter
    content = fs.read_file_content(str(legacy_file))

    # 3. ASSERT: No crash occurred. The special chars will be mangled (replaced by ),
    # but the application must survive.
    assert "A" in content
    assert "o de creaci" in content
    assert "\ufffd" in content

@pytest.mark.integration
def test_stream_file_content_handles_mixed_content_safely(tmp_path: Path):
    """
    Ensures that the chunked/streaming reader used by the pipeline workers
    does not break mid-iteration when it encounters a line with bad bytes.
    """
    # 1. ARRANGE: Write valid lines followed by a corrupted line
    mixed_file = tmp_path / "mixed.log"
    with open(mixed_file, "wb") as f:
        f.write(b"Line 1: Valid UTF-8\n")
        f.write(b"Line 2: Valid UTF-8\n")
        f.write(b"Line 3: Corrupt \x80\x81 bytes\n")
        f.write(b"Line 4: Recovered UTF-8\n")

    # 2. ACT: Consume the stream into a list of lines
    lines = list(stream_file_content(str(mixed_file)))

    # 3. ASSERT: All 4 lines were processed without breaking the generator
    assert len(lines) == 4
    assert "Line 1: Valid UTF-8" in lines[0]
    assert "\ufffd" in lines[2]  # The corrupted line must contain the replacement char
    assert "Line 4: Recovered UTF-8" in lines[3]

@pytest.mark.integration
def test_read_file_safely_wrapper_preserves_resilience(tmp_path: Path):
    """
    Verifies that the `read_file_safely` wrapper used in the application layer
    inherits the exact same encoding protection.
    """
    # 1. ARRANGE: Create an invalid byte sequence
    bad_file = tmp_path / "bad.txt"
    bad_file.write_bytes(b"\x80")

    # 2. ACT: Read using the pipeline component
    content = read_file_safely(str(bad_file))

    # 3. ASSERT: Returns the replacement char instead of crashing
    assert content == "\ufffd"