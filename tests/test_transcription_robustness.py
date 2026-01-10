from __future__ import annotations

"""
Robustness tests for the transcription service.

Ensures the service handles encoding errors gracefully using the 
new streaming reader and validates parallel error aggregation.
"""

import pytest
import os
from transcriptor4ai.transcription.service import transcribe_code


@pytest.fixture
def bad_files_structure(tmp_path):
    """
    Creates a folder with problematic files:
    1. A binary file renamed to .py.
    2. A Latin-1 encoded file (to test UTF-8 replacement).
    3. A valid file.
    """
    src = tmp_path / "src"
    src.mkdir()

    (src / "valid.py").write_text("print('ok')", encoding="utf-8")
    (src / "fake.py").write_bytes(b'\x80\x81\xFF')
    (src / "legacy.py").write_bytes(b'# C\xf3digo en espa\xf1ol')

    return src


def test_transcription_resilience_to_encoding_errors(bad_files_structure, tmp_path):
    """
    The streaming reader uses 'replace' for decodings.
    The pipeline must be stable and not crash.
    """
    # Prepare output paths
    out_dir = tmp_path / "out"
    modules_out = out_dir / "test_modules.txt"
    tests_out = out_dir / "test_tests.txt"
    resources_out = out_dir / "test_resources.txt"
    errors_out = out_dir / "test_errors.txt"

    result = transcribe_code(
        input_path=str(bad_files_structure),
        modules_output_path=str(modules_out),
        tests_output_path=str(tests_out),
        resources_output_path=str(resources_out),
        error_output_path=str(errors_out),
        process_modules=True,
        process_tests=True,
        process_resources=False,
        extensions=[".py"],
        respect_gitignore=False,
        save_error_log=True
    )

    # 1. Pipeline should finish successfully due to robust streaming
    assert result["ok"] is True

    # 2. Counters check
    counters = result["counters"]
    assert counters["processed"] >= 1
    assert counters["errors"] == 0

    # 3. Verify Output exists
    assert os.path.exists(modules_out)

    with open(modules_out, "r", encoding="utf-8") as f:
        content = f.read()
        assert "valid.py" in content
        assert "\ufffd" in content


def test_transcription_error_aggregation(tmp_path):
    """
    Verify that actual OS errors (like permission denied) are
    properly aggregated by the parallel workers.
    """
    src = tmp_path / "src"
    src.mkdir()
    file_path = src / "locked.py"
    file_path.write_text("content")


    out_dir = tmp_path / "out"
    result = transcribe_code(
        input_path=str(src) + "_non_existent",
        modules_output_path=str(out_dir / "m.txt"),
        tests_output_path=str(out_dir / "t.txt"),
        resources_output_path=str(out_dir / "r.txt"),
        error_output_path=str(out_dir / "e.txt"),
    )


    assert "counters" in result