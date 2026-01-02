# tests/test_pipeline_integration.py
import os
import pytest
from transcriptor4ai.pipeline import run_pipeline


@pytest.fixture
def source_structure(tmp_path):
    """
    Creates a temporary file structure for testing the pipeline:
    /src/main.py
    /src/utils.py
    /tests/test_main.py
    /ignored/__init__.py
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass", encoding="utf-8")
    (src / "utils.py").write_text("class Utils: pass", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_one(): pass", encoding="utf-8")

    return tmp_path


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

def test_pipeline_dry_run_does_not_write(source_structure):
    """Dry run should return OK but create no output files."""
    config = {
        "ruta_carpetas": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "out",
        "output_prefix": "dry",
        "modo_procesamiento": "todo"
    }

    result = run_pipeline(config, dry_run=True)

    assert result.ok is True
    assert result.resumen["dry_run"] is True

    # Verify folder was NOT created or is empty
    out_dir = source_structure / "out"
    if out_dir.exists():
        assert len(list(out_dir.iterdir())) == 0


def test_pipeline_full_execution(source_structure):
    """Full execution should generate module and test text files."""
    config = {
        "ruta_carpetas": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "final",
        "output_prefix": "res",
        "modo_procesamiento": "todo",
        "generar_arbol": True
    }

    result = run_pipeline(config, dry_run=False)

    assert result.ok is True

    out_dir = source_structure / "final"
    assert out_dir.exists()

    # Check Modulos
    mod_file = out_dir / "res_modulos.txt"
    assert mod_file.exists()
    content_mod = mod_file.read_text(encoding="utf-8")
    assert "src/main.py" in content_mod or "src\\main.py" in content_mod
    assert "src/utils.py" in content_mod or "src\\utils.py" in content_mod

    # Check Tests
    test_file = out_dir / "res_tests.txt"
    assert test_file.exists()
    content_test = test_file.read_text(encoding="utf-8")
    assert "tests/test_main.py" in content_test or "tests\\test_main.py" in content_test

    # Check Tree
    tree_file = out_dir / "res_arbol.txt"
    assert tree_file.exists()


def test_pipeline_overwrite_protection(source_structure):
    """Pipeline should fail if files exist and overwrite is False."""
    out_dir = source_structure / "protect"
    out_dir.mkdir()

    # Create a conflict file
    (out_dir / "conflict_modulos.txt").write_text("exists")

    config = {
        "ruta_carpetas": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "protect",
        "output_prefix": "conflict",
        "modo_procesamiento": "todo"
    }

    # First run: Should fail (ok=False) because file exists
    result = run_pipeline(config, overwrite=False)
    assert result.ok is False
    assert "existing files" in result.error.lower() or "existing files" in str(result.resumen)

    # Second run: Should succeed with overwrite=True
    result_force = run_pipeline(config, overwrite=True)
    assert result_force.ok is True