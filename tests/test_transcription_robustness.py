# tests/test_transcription_robustness.py
import pytest
import os
from transcriptor4ai.transcription.service import transcribir_codigo


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

    result = transcribir_codigo(
        ruta_base=str(bad_files_structure),
        modo="todo",
        extensiones=[".py"],
        output_folder=str(out_dir),
        guardar_log_errores=True
    )

    # 1. Pipeline should finish successfully (partial success)
    assert result["ok"] is True

    # 2. Counters check
    # We have 3 files. 1 valid, 2 invalid.
    # Logic in service: try read -> except -> add to errors -> continue
    # So 'procesados' counts successfully written files.
    # 'errores' counts files that raised exception.
    counters = result["contadores"]
    assert counters["procesados"] == 1  # Only valid.py
    assert counters["errores"] == 2  # fake.py and legacy.py

    # 3. Verify Error Log existence
    error_log_path = result["generados"]["errores"]
    assert os.path.exists(error_log_path)

    # 4. Verify Content of Error Log
    with open(error_log_path, "r", encoding="utf-8") as f:
        log_content = f.read()
        assert "fake.py" in log_content
        assert "legacy.py" in log_content