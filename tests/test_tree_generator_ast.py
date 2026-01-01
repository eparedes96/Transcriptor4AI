# tests/test_tree_generator_ast.py
# -----------------------------------------------------------------------------
# Unit tests for extraer_funciones_clases() in tree_generator.py.
# Focus:
# - extracting top-level functions and classes
# - optional extraction of class methods
# - error handling: SyntaxError, OSError, UnicodeDecodeError
# - behavior boundaries: nested functions not listed
# -----------------------------------------------------------------------------

from __future__ import annotations

import builtins
from pathlib import Path

import tree_generator as tg


def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_ast_extracts_top_level_functions(tmp_path):
    f = tmp_path / "a.py"
    _write(f, "def top():\n    return 1\n\nclass C:\n    pass\n")

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=False, mostrar_metodos=False)
    assert res == ["Función: top()"]


def test_ast_extracts_top_level_classes(tmp_path):
    f = tmp_path / "a.py"
    _write(f, "def top():\n    return 1\n\nclass C:\n    pass\n")

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=False, mostrar_clases=True, mostrar_metodos=False)
    assert res == ["Clase: C"]


def test_ast_extracts_methods_when_enabled(tmp_path):
    f = tmp_path / "a.py"
    _write(
        f,
        "class C:\n"
        "    def m1(self):\n"
        "        return 1\n"
        "    def m2(self):\n"
        "        return 2\n"
        "\n"
        "def top():\n"
        "    return 3\n"
    )

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=False, mostrar_clases=True, mostrar_metodos=True)

    assert "Clase: C" in res
    assert "  Método: m1()" in res
    assert "  Método: m2()" in res
    # In this configuration, top-level functions are not included
    assert all("top()" not in x for x in res)


def test_ast_no_symbols_returns_empty_list(tmp_path):
    f = tmp_path / "a.py"
    _write(f, "# no symbols here\nx = 1\n")

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=True, mostrar_metodos=True)
    assert res == []


def test_ast_syntax_error_returns_error_line(tmp_path):
    f = tmp_path / "bad.py"
    _write(f, "def oops(:\n    pass\n")  # invalid

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=True, mostrar_metodos=True)
    assert len(res) == 1
    assert res[0].startswith("[ERROR] AST inválido (SyntaxError):")


def test_ast_read_oserror_returns_error_line(monkeypatch, tmp_path):
    f = tmp_path / "a.py"
    _write(f, "def top():\n    return 1\n")

    real_open = builtins.open

    def boom(path, mode="r", *args, **kwargs):
        if str(path).endswith("a.py") and "r" in mode:
            raise OSError("blocked")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", boom)

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=True, mostrar_metodos=True)
    assert len(res) == 1
    assert res[0].startswith("[ERROR] No se pudo leer")
    assert "blocked" in res[0]


def test_ast_unicode_error_returns_error_line(monkeypatch, tmp_path):
    f = tmp_path / "a.py"
    _write(f, "def top():\n    return 1\n")

    real_open = builtins.open

    class BadFile:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "bad")

    def selective_open(path, mode="r", *args, **kwargs):
        if str(path).endswith("a.py") and "r" in mode:
            return BadFile()
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", selective_open)

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=True, mostrar_metodos=True)
    assert len(res) == 1
    assert res[0].startswith("[ERROR] No se pudo leer")


def test_ast_does_not_list_nested_functions(tmp_path):
    f = tmp_path / "a.py"
    _write(
        f,
        "def outer():\n"
        "    def inner():\n"
        "        return 1\n"
        "    return inner()\n"
    )

    res = tg.extraer_funciones_clases(str(f), mostrar_funciones=True, mostrar_clases=True, mostrar_metodos=True)
    # Only top-level defs are included
    assert res == ["Función: outer()"]