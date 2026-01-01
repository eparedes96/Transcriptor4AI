# tests/test_code_transcriptor_functional.py
# -----------------------------------------------------------------------------
# Functional unit tests for transcribir_codigo() using tmp_path.
# Focus:
# - file selection (extensions, include/exclude, directory exclusion)
# - mode behavior (all/solo_tests/solo_modulos)
# - output format and relative paths
# - error handling (read/write/output folder)
# - return payload consistency
# -----------------------------------------------------------------------------

from __future__ import annotations

import builtins
import os
from pathlib import Path

import code_transcriptor as ct


# -----------------------------------------------------------------------------
# Helpers for tests
# -----------------------------------------------------------------------------

def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _read_text(p: Path) -> str:
    return p.read_text(encoding="utf-8")


def _make_sample_tree(base: Path) -> dict[str, Path]:
    """
    Create a representative directory tree.

    base/
      a.py
      b.txt
      test_one.py
      mod_test.py
      __pycache__/ignored.py
      .hidden/ignored2.py
      pkg/__init__.py
      pkg/c.py
      pkg/test_pkg.py
      docs/readme.md
    """
    paths: dict[str, Path] = {}

    paths["a.py"] = base / "a.py"
    _write(paths["a.py"], "def a():\n    return 1\n")

    paths["b.txt"] = base / "b.txt"
    _write(paths["b.txt"], "not python\n")

    paths["test_one.py"] = base / "test_one.py"
    _write(paths["test_one.py"], "def test_one():\n    assert True\n")

    paths["mod_test.py"] = base / "mod_test.py"
    _write(paths["mod_test.py"], "def test_mod():\n    assert True\n")

    paths["pycache_ignored"] = base / "__pycache__" / "ignored.py"
    _write(paths["pycache_ignored"], "def should_not_be_seen():\n    pass\n")

    paths["hidden_ignored"] = base / ".hidden" / "ignored2.py"
    _write(paths["hidden_ignored"], "def should_not_be_seen2():\n    pass\n")

    paths["init_ignored"] = base / "pkg" / "__init__.py"
    _write(paths["init_ignored"], "# init\n")

    paths["c.py"] = base / "pkg" / "c.py"
    _write(paths["c.py"], "class C:\n    pass\n")

    paths["test_pkg.py"] = base / "pkg" / "test_pkg.py"
    _write(paths["test_pkg.py"], "def test_pkg():\n    assert True\n")

    paths["readme.md"] = base / "docs" / "readme.md"
    _write(paths["readme.md"], "# docs\n")

    return paths


def _run(
    ruta_base: Path,
    out_dir: Path,
    modo: str = "todo",
    extensiones=None,
    patrones_incluir=None,
    patrones_excluir=None,
    prefix: str = "out",
    guardar_log_errores: bool = True,
):
    return ct.transcribir_codigo(
        ruta_base=str(ruta_base),
        modo=modo,
        extensiones=extensiones,
        patrones_incluir=patrones_incluir,
        patrones_excluir=patrones_excluir,
        archivo_salida=prefix,
        output_folder=str(out_dir),
        guardar_log_errores=guardar_log_errores,
    )


# -----------------------------------------------------------------------------
# File selection / filtering
# -----------------------------------------------------------------------------

def test_transcribir_filters_by_extension(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, extensiones=[".py"], prefix="t1")
    assert res["ok"] is True

    mod_text = _read_text(out / "t1_modulos.txt")
    test_text = _read_text(out / "t1_tests.txt")

    assert "b.txt" not in mod_text
    assert "b.txt" not in test_text
    assert "a.py" in mod_text
    assert "test_one.py" in test_text


def test_transcribir_applies_include_patterns(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    # Only include files starting with "a" or "test_"
    res = _run(base, out, patrones_incluir=[r"^(a\.py|test_.*\.py)$"], prefix="t2")
    assert res["ok"] is True

    mod_text = _read_text(out / "t2_modulos.txt")
    test_text = _read_text(out / "t2_tests.txt")

    assert "a.py" in mod_text
    assert "test_one.py" in test_text
    assert "mod_test.py" not in test_text
    assert "pkg/c.py" not in mod_text


def test_transcribir_applies_exclude_patterns_to_files(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    # Exclude a.py specifically
    res = _run(base, out, patrones_excluir=[r"^a\.py$"], prefix="t3")
    assert res["ok"] is True

    mod_text = _read_text(out / "t3_modulos.txt")
    assert "a.py" not in mod_text


def test_transcribir_excludes_directories_pycache_git_hidden(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, prefix="t4")
    assert res["ok"] is True

    mod_text = _read_text(out / "t4_modulos.txt")
    test_text = _read_text(out / "t4_tests.txt")

    # Should not include from __pycache__ or hidden dirs by default patterns
    assert "ignored.py" not in mod_text
    assert "ignored2.py" not in mod_text
    assert "ignored.py" not in test_text
    assert "ignored2.py" not in test_text


# -----------------------------------------------------------------------------
# Mode behavior
# -----------------------------------------------------------------------------

def test_transcribir_mode_todo_generates_tests_and_modules(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, modo="todo", prefix="m1")
    assert res["ok"] is True
    assert (out / "m1_tests.txt").exists()
    assert (out / "m1_modulos.txt").exists()

    mod_text = _read_text(out / "m1_modulos.txt")
    test_text = _read_text(out / "m1_tests.txt")

    assert "a.py" in mod_text
    assert "test_one.py" in test_text


def test_transcribir_mode_solo_tests_generates_only_tests_file(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, modo="solo_tests", prefix="m2")
    assert res["ok"] is True
    assert (out / "m2_tests.txt").exists()
    assert not (out / "m2_modulos.txt").exists()

    test_text = _read_text(out / "m2_tests.txt")
    assert "test_one.py" in test_text
    assert "a.py" not in test_text


def test_transcribir_mode_solo_modulos_generates_only_modules_file(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, modo="solo_modulos", prefix="m3")
    assert res["ok"] is True
    assert (out / "m3_modulos.txt").exists()
    assert not (out / "m3_tests.txt").exists()

    mod_text = _read_text(out / "m3_modulos.txt")
    assert "a.py" in mod_text
    assert "test_one.py" not in mod_text


# -----------------------------------------------------------------------------
# Output format
# -----------------------------------------------------------------------------

def test_output_has_header_and_separator_and_relpath(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, modo="todo", prefix="fmt1")
    assert res["ok"] is True

    text = _read_text(out / "fmt1_modulos.txt")

    assert text.startswith("CODIGO:\n")
    assert ("-" * 200 + "\n") in text

    # rel paths should appear (root file and nested)
    assert "\na.py\n" in text
    assert "\npkg{}c.py\n".format(os.sep) in text or "\npkg/c.py\n" in text


def test_output_separator_is_200_dashes(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    _run(base, out, prefix="fmt2")
    text = _read_text(out / "fmt2_modulos.txt")

    assert ("-" * 200 + "\n") in text
    assert ("-" * 199 + "\n") not in text


def test_output_content_newlines_are_normalized(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    base.mkdir(parents=True, exist_ok=True)

    _write(base / "a.py", "line1\nline2\n\n")
    _run(base, out, prefix="fmt3")

    text = _read_text(out / "fmt3_modulos.txt")
    # Ensure at least one newline at the end and no crash; exact policy is minimal here
    assert text.endswith("\n")


# -----------------------------------------------------------------------------
# Error handling (read/write/output folder)
# -----------------------------------------------------------------------------

def test_output_folder_creation_failure_returns_ok_false(monkeypatch, tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    def boom(*args, **kwargs):
        raise OSError("cannot create")

    monkeypatch.setattr(os, "makedirs", boom)

    res = _run(base, out, prefix="e1")
    assert res["ok"] is False
    assert "cannot create" in res.get("error", "")


def test_read_oserror_is_logged_and_counted(monkeypatch, tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    real_open = builtins.open

    def selective_open(path, *args, **kwargs):
        # Fail reading a specific file
        if str(path).endswith(os.path.join("", "a.py")) and "r" in (args[0] if args else kwargs.get("mode", "r")):
            raise OSError("blocked")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", selective_open)

    res = _run(base, out, prefix="e2", guardar_log_errores=True)
    assert res["ok"] is True
    assert res["contadores"]["errores"] >= 1

    err_log = out / "e2_errores.txt"
    assert err_log.exists()
    txt = _read_text(err_log)
    assert "a.py" in txt
    assert "blocked" in txt


def test_read_unicode_error_is_logged_and_counted(monkeypatch, tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    real_open = builtins.open

    class BadFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")

    def selective_open(path, *args, **kwargs):
        if str(path).endswith(os.path.join("", "a.py")) and "r" in (args[0] if args else kwargs.get("mode", "r")):
            return BadFile()
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", selective_open)

    res = _run(base, out, prefix="e3", guardar_log_errores=True)
    assert res["ok"] is True
    assert res["contadores"]["errores"] >= 1

    txt = _read_text(out / "e3_errores.txt")
    assert "a.py" in txt


def test_write_oserror_is_logged_and_counted(monkeypatch, tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    real_open = builtins.open

    def selective_open(path, *args, **kwargs):
        # Fail appending to modules output
        if str(path).endswith("e4_modulos.txt") and "a" in (args[0] if args else kwargs.get("mode", "")):
            raise OSError("cannot write")
        return real_open(path, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", selective_open)

    res = _run(base, out, prefix="e4", guardar_log_errores=True)
    assert res["ok"] is True
    assert res["contadores"]["errores"] >= 1

    txt = _read_text(out / "e4_errores.txt")
    assert "Error escribiendo salida" in txt or "cannot write" in txt


# -----------------------------------------------------------------------------
# Error log behavior and return payload
# -----------------------------------------------------------------------------

def test_error_log_not_created_when_disabled(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, prefix="log1", guardar_log_errores=False)
    assert res["ok"] is True
    assert not (out / "log1_errores.txt").exists()


def test_return_payload_contains_expected_keys_and_paths(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, prefix="ret1", modo="todo")
    assert res["ok"] is True

    assert "ruta_base" in res
    assert "output_folder" in res
    assert "generados" in res
    assert "contadores" in res

    gen = res["generados"]
    assert gen["tests"].endswith("ret1_tests.txt")
    assert gen["modulos"].endswith("ret1_modulos.txt")


def test_counters_are_consistent(tmp_path):
    base = tmp_path / "base"
    out = tmp_path / "out"
    _make_sample_tree(base)

    res = _run(base, out, prefix="cnt1", modo="todo")
    assert res["ok"] is True

    cont = res["contadores"]
    assert cont["procesados"] >= 1
    assert cont["tests_escritos"] >= 1
    assert cont["modulos_escritos"] >= 1
    assert cont["errores"] >= 0
