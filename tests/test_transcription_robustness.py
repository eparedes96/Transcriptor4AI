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
    (src / "fake.py").write_bytes(b'\x80\x81\xFF')

    # Latin-1 file with special chars (e.g., ñ, á)
    (src / "legacy.py").write_bytes(b'# C\xf3digo en espa\xf1ol')

    return src


def test_transcription_resilience_to_encoding_errors(bad_files_structure, tmp_path):
    """
    The pipeline must NOT crash when encountering bad encodings.
    It should skip the file and record an error.
    """
    # Prepare output paths
    out_dir = tmp_path / "out"
    modules_out = out_dir / "test_modules.txt"
    tests_out = out_dir / "test_tests.txt"
    errors_out = out_dir / "test_errors.txt"

    result = transcribe_code(
        input_path=str(bad_files_structure),
        modules_output_path=str(modules_out),
        tests_output_path=str(tests_out),
        error_output_path=str(errors_out),
        process_modules=True,
        process_tests=True,
        extensions=[".py"],
        save_error_log=True
    )

    # 1. Pipeline should finish successfully (partial success)
    assert result["ok"] is True

    # 2. Counters check
    counters = result["counters"]
    assert counters["processed"] == 1
    assert counters["errors"] == 2

    # 3. Verify Error Log existence
    error_log_path = result["generated"]["errors"]
    assert error_log_path != ""
    assert os.path.exists(error_log_path)
    assert os.path.exists(errors_out)

    # 4. Verify Content of Error Log
    with open(error_log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "fake.py" in log_content
        assert "legacy.py" in log_content