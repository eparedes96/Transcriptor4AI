# tests/test_integration_pipeline.py
# -----------------------------------------------------------------------------
# Minimal integration tests (no GUI):
# - Create a small repo tree
# - Run transcribir_codigo() into output_base/subdir
# - Run generar_arbol_directorios() saving tree file
# - Verify expected outputs exist and contain expected markers
#
# Focus:
# - output subdir creation pattern
# - non-ascii paths handling
# - basic cross-platform path sanity (relpath appears)
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
from pathlib import Path

import code_transcriptor as ct
import tree_generator as tg


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _make_repo(base: Path) -> None:
    """
    base/
      a.py
      test_a.py
      pkg/c.py
      pkg/c_test.py
      __pycache__/ignored.py
      .hidden/ignored2.py
    """
    _write(base / "a.py", "def a():\n    return 1\n")
    _write(base / "test_a.py", "def test_a():\n    assert True\n")
    _write(base / "pkg" / "c.py", "class C:\n    pass\n")
    _write(base / "pkg" / "c_test.py", "def test_c():\n    assert True\n")
    _write(base / "__pycache__" / "ignored.py", "def ignored():\n    pass\n")
    _write(base / ".hidden" / "ignored2.py", "def ignored2():\n    pass\n")


def _pipeline(
    ruta_base: Path,
    output_base: Path,
    subdir: str,
    prefix: str,
    modo: str = "todo",
) -> Path:
    salida_real = output_base / subdir
    salida_real.mkdir(parents=True, exist_ok=True)

    res = ct.transcribir_codigo(
        ruta_base=str(ruta_base),
        modo=modo,
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=ct._default_patrones_excluir(),
        archivo_salida=prefix,
        output_folder=str(salida_real),
        guardar_log_errores=True,
    )
    assert res["ok"] is True

    tree_file = salida_real / f"{prefix}_arbol.txt"
    tg.generar_arbol_directorios(
        ruta_base=str(ruta_base),
        modo=modo,
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        mostrar_funciones=True,
        mostrar_clases=True,
        mostrar_metodos=True,
        imprimir=False,
        guardar_archivo=str(tree_file),
    )

    return salida_real


# -----------------------------------------------------------------------------
# Tests
# -----------------------------------------------------------------------------

def test_pipeline_creates_output_subdir_and_expected_files(tmp_path):
    repo = tmp_path / "repo"
    _make_repo(repo)

    out_base = tmp_path / "out_base"
    subdir = "transcript"
    prefix = "transcripcion"

    salida_real = _pipeline(repo, out_base, subdir, prefix, modo="todo")

    # Expected files
    assert (salida_real / f"{prefix}_modulos.txt").exists()
    assert (salida_real / f"{prefix}_tests.txt").exists()
    assert (salida_real / f"{prefix}_errores.txt").exists()
    assert (salida_real / f"{prefix}_arbol.txt").exists()

    # Contents sanity
    mod_txt = (salida_real / f"{prefix}_modulos.txt").read_text(encoding="utf-8")
    tests_txt = (salida_real / f"{prefix}_tests.txt").read_text(encoding="utf-8")
    tree_txt = (salida_real / f"{prefix}_arbol.txt").read_text(encoding="utf-8")

    assert mod_txt.startswith("CODIGO:\n")
    assert tests_txt.startswith("CODIGO:\n")
    assert "a.py" in mod_txt
    assert "test_a.py" in tests_txt
    assert "pkg" in tree_txt
    assert "Función:" in tree_txt or "Clase:" in tree_txt  # depending on content


def test_pipeline_handles_non_ascii_paths(tmp_path):
    repo = tmp_path / "repositorio_á"
    _make_repo(repo)

    out_base = tmp_path / "salida_ñ"
    subdir = "transcript"
    prefix = "transcripcion"

    salida_real = _pipeline(repo, out_base, subdir, prefix, modo="todo")

    # Should still generate files correctly
    assert (salida_real / f"{prefix}_modulos.txt").exists()
    assert (salida_real / f"{prefix}_tests.txt").exists()
    assert (salida_real / f"{prefix}_arbol.txt").exists()


def test_pipeline_cross_platform_relpath_sanity(tmp_path):
    repo = tmp_path / "repo"
    _make_repo(repo)

    out_base = tmp_path / "out_base"
    subdir = "transcript"
    prefix = "transcripcion"

    salida_real = _pipeline(repo, out_base, subdir, prefix, modo="todo")

    mod_txt = (salida_real / f"{prefix}_modulos.txt").read_text(encoding="utf-8")

    # We expect relative paths (not absolute) to appear; allow either separator.
    assert "\na.py\n" in mod_txt
    # nested path should appear as relpath
    assert "\npkg{}c.py\n".format(os.sep) in mod_txt or "\npkg/c.py\n" in mod_txt or "\npkg\\c.py\n" in mod_txt


def test_pipeline_overwrite_is_file_based(tmp_path):
    """
    This test validates the *concept* that overwrite concerns should be based on
    existing target files, not the output directory. Since the GUI prompt is not
    invoked here, we assert that rerunning the pipeline keeps the same output
    directory and overwrites the same target files without creating extra dirs.
    """
    repo = tmp_path / "repo"
    _make_repo(repo)

    out_base = tmp_path / "out_base"
    subdir = "transcript"
    prefix = "transcripcion"

    salida_real_1 = _pipeline(repo, out_base, subdir, prefix, modo="todo")
    files_1 = sorted([p.name for p in salida_real_1.iterdir() if p.is_file()])

    # Modify a source file to ensure outputs change
    _write(repo / "a.py", "def a():\n    return 999\n")

    salida_real_2 = _pipeline(repo, out_base, subdir, prefix, modo="todo")
    files_2 = sorted([p.name for p in salida_real_2.iterdir() if p.is_file()])

    assert salida_real_1 == salida_real_2
    assert files_1 == files_2  # same set of outputs, no extra directories

    mod_txt = (salida_real_2 / f"{prefix}_modulos.txt").read_text(encoding="utf-8")
    assert "return 999" in mod_txt