from __future__ import annotations

"""
Robustness tests for the transcription service.

Ensures the service handles encoding errors gracefully and 
validates the lazy writing logic for error logs.
"""

import pytest
import os
from transcriptor4ai.transcription.service import transcribe_code


@pytest.fixture
def bad_files_structure(tmp_path):
    """
    Creates a folder with problematic files:
    1. A binary file renamed to .py (UnicodeDecodeError scenario).
    2. A Latin-1 encoded file (UnicodeDecodeError scenario if read as UTF-8).
    3. A valid file.
    """
    src = tmp_path / "src"
    src.mkdir()

    # Valid file
    (src / "valid.py").write_text("print('ok')", encoding="utf-8")

    # Binary file disguised as python
    # Writing random bytes that are invalid UTF-8 start bytes
    (src / "fake.py").write_bytes(b'\x80\x81\xFF')

    # Latin-1 file with special chars (e.g., ñ, á)
    # This might fail strict UTF-8 decoding
    (src / "legacy.py").write_bytes(b'# C\xf3digo en espa\xf1ol')  # Código en español in Latin-1

    return src


def test_transcription_resilience_to_encoding_errors(bad_files_structure, tmp_path):
    """
    The pipeline must NOT crash when encountering bad encodings.
    It should skip the file and record an error.
    """
    out_dir = tmp_path / "out"

    result = transcribe_code(
        input_path=str(bad_files_structure),
        mode="todo",
        extensions=[".py"],
        output_folder=str(out_dir),
        save_error_log=True
    )

    # 1. Pipeline should finish successfully (partial success)
    assert result["ok"] is True

    # 2. Counters check
    # We have 3 files. 1 valid, 2 invalid.
    counters = result["counters"]
    assert counters["processed"] == 1  # Only valid.py
    assert counters["errors"] == 2     # fake.py and legacy.py

    # 3. Verify Error Log existence (Lazy Writing: created because errors > 0)
    error_log_path = result["generated"]["errors"]
    assert error_log_path != ""
    assert os.path.exists(error_log_path)

    # 4. Verify Content of Error Log
    with open(error_log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "fake.py" in log_content
        assert "legacy.py" in log_content