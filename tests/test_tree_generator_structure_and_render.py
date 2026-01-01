# tests/test_tree_generator_structure_and_render.py
# -----------------------------------------------------------------------------
# Tests for:
# - construir_estructura() filesystem -> Tree
# - generar_estructura_texto() Tree -> list[str]
# - generar_arbol_directorios() orchestration (return lines, optional printing)
# - saving to file + error-path behavior
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
from pathlib import Path

import tree_generator as tg


# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def _write(p: Path, content: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _make_tree(base: Path) -> dict[str, Path]:
    """
    base/
      a.py
      test_one.py
      mod_test.py
      pkg/c.py
      pkg/test_pkg.py
      __pycache__/ignored.py
      .hidden/ignored2.py
      notes.txt
    """
    paths: dict[str, Path] = {}

    paths["a.py"] = base / "a.py"
    _write(paths["a.py"], "def a():\n    return 1\n")

    paths["test_one.py"] = base / "test_one.py"
    _write(paths["test_one.py"], "def test_one():\n    assert True\n")

    paths["mod_test.py"] = base / "mod_test.py"
    _write(paths["mod_test.py"], "def test_mod():\n    assert True\n")

    paths["c.py"] = base / "pkg" / "c.py"
    _write(paths["c.py"], "class C:\n    pass\n")

    paths["test_pkg.py"] = base / "pkg" / "test_pkg.py"
    _write(paths["test_pkg.py"], "def test_pkg():\n    assert True\n")

    paths["pycache_ignored"] = base / "__pycache__" / "ignored.py"
    _write(paths["pycache_ignored"], "def ignored():\n    pass\n")

    paths["hidden_ignored"] = base / ".hidden" / "ignored2.py"
    _write(paths["hidden_ignored"], "def ignored2():\n    pass\n")

    paths["notes.txt"] = base / "notes.txt"
    _write(paths["notes.txt"], "hello\n")

    return paths


def _build_structure(base: Path, modo: str = "todo"):
    incluir = tg._compile_patterns([".*"])
    excluir = tg._compile_patterns(tg._default_patrones_excluir())
    return tg.construir_estructura(
        ruta_base=str(base),
        modo=modo,
        extensiones=[".py"],
        incluir_rx=incluir,
        excluir_rx=excluir,
        es_test_func=tg._es_test,
    )


def _render_root_entries(estructura: dict) -> list[str]:
    """
    Render only the root level and return the displayed entry names in order.
    """
    lines: list[str] = []
    tg.generar_estructura_texto(
        estructura,
        lines,
        prefix="",
        mostrar_funciones=False,
        mostrar_clases=False,
        mostrar_metodos=False,
    )
    entries: list[str] = []
    for ln in lines:
        if ln.startswith(("├── ", "└── ")):
            entries.append(ln[4:])
    return entries


# -----------------------------------------------------------------------------
# construir_estructura
# -----------------------------------------------------------------------------

def test_build_structure_creates_nested_tree(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="todo")

    assert "a.py" in estructura
    assert "test_one.py" in estructura
    assert "mod_test.py" in estructura
    assert "pkg" in estructura
    assert isinstance(estructura["pkg"], dict)
    assert "c.py" in estructura["pkg"]
    assert "test_pkg.py" in estructura["pkg"]


def test_build_structure_filters_extensions_and_patterns(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    incluir = tg._compile_patterns([r"^(a\.py|c\.py)$"])
    excluir = tg._compile_patterns(tg._default_patrones_excluir())

    estructura = tg.construir_estructura(
        ruta_base=str(base),
        modo="todo",
        extensiones=[".py"],
        incluir_rx=incluir,
        excluir_rx=excluir,
        es_test_func=tg._es_test,
    )

    assert "a.py" in estructura
    assert "test_one.py" not in estructura
    assert "mod_test.py" not in estructura
    assert "pkg" in estructura
    assert "c.py" in estructura["pkg"]
    assert "test_pkg.py" not in estructura["pkg"]


def test_build_structure_respects_mode_solo_tests(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="solo_tests")

    assert "a.py" not in estructura
    assert "test_one.py" in estructura
    assert "mod_test.py" in estructura
    assert "pkg" in estructura
    assert "c.py" not in estructura["pkg"]
    assert "test_pkg.py" in estructura["pkg"]


def test_build_structure_respects_mode_solo_modulos(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="solo_modulos")

    assert "a.py" in estructura
    assert "test_one.py" not in estructura
    assert "mod_test.py" not in estructura
    assert "pkg" in estructura
    assert "c.py" in estructura["pkg"]
    assert "test_pkg.py" not in estructura["pkg"]


def test_build_structure_excludes_directories_pycache_hidden(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="todo")

    assert "__pycache__" not in estructura
    assert ".hidden" not in estructura


def test_build_structure_file_node_path_is_full_path(tmp_path):
    base = tmp_path / "base"
    paths = _make_tree(base)

    estructura = _build_structure(base, modo="todo")
    node = estructura["a.py"]
    assert isinstance(node, tg.FileNode)
    assert os.path.abspath(node.path) == os.path.abspath(str(paths["a.py"]))


def test_build_structure_is_sorted_stable(tmp_path):
    """
    Ordering contract is validated on the rendered output (deterministic),
    not on the dict insertion order.
    """
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="todo")

    entries = _render_root_entries(estructura)

    assert entries == sorted(entries)

    lines: list[str] = []
    tg.generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=False, mostrar_clases=False, mostrar_metodos=False)
    pkg_children = []
    in_pkg = False
    for ln in lines:
        if ln.startswith(("├── ", "└── ")) and ln[4:] == "pkg":
            in_pkg = True
            continue
        if in_pkg and ln.startswith(("├── ", "└── ")) and not ln.startswith("│   "):
            break
        if in_pkg and ("│   " in ln or ln.startswith("    ")):
            stripped = ln.replace("│   ", "").replace("    ", "")
            if stripped.startswith(("├── ", "└── ")):
                pkg_children.append(stripped[4:])

    assert pkg_children == sorted(pkg_children)


# -----------------------------------------------------------------------------
# generar_estructura_texto / generar_arbol_directorios
# -----------------------------------------------------------------------------

def test_render_connectors_and_prefix_alignment_simple_tree(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    estructura = _build_structure(base, modo="solo_modulos")
    lines = []
    tg.generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=False, mostrar_clases=False, mostrar_metodos=False)

    assert any(line.startswith(("├── ", "└── ")) for line in lines)
    assert any("pkg" in line for line in lines)
    assert any("c.py" in line for line in lines)
    assert any(("│   " in line or "    " in line) and "c.py" in line for line in lines)


def test_render_empty_tree_is_empty_lines(tmp_path):
    base = tmp_path / "base"
    base.mkdir(parents=True, exist_ok=True)

    estructura = _build_structure(base, modo="todo")
    lines = []
    tg.generar_estructura_texto(estructura, lines)

    assert lines == []


def test_generar_arbol_directorios_returns_lines(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    lines = tg.generar_arbol_directorios(
        ruta_base=str(base),
        modo="todo",
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        mostrar_funciones=False,
        mostrar_clases=False,
        mostrar_metodos=False,
        imprimir=False,
        guardar_archivo="",
    )

    assert isinstance(lines, list)
    assert any("a.py" in l for l in lines)
    assert any("pkg" in l for l in lines)


def test_generar_arbol_directorios_imprimir_false_no_stdout(tmp_path, capsys):
    base = tmp_path / "base"
    _make_tree(base)

    tg.generar_arbol_directorios(
        ruta_base=str(base),
        modo="todo",
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        imprimir=False,
    )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_save_tree_creates_parent_dir_and_writes_file(tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    out_file = tmp_path / "nested" / "dir" / "tree.txt"

    lines = tg.generar_arbol_directorios(
        ruta_base=str(base),
        modo="todo",
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        imprimir=False,
        guardar_archivo=str(out_file),
    )

    assert out_file.exists()
    content = out_file.read_text(encoding="utf-8")
    assert "\n".join(lines) in content
    assert "a.py" in content


def test_save_tree_write_failure_appends_error_line(monkeypatch, tmp_path):
    base = tmp_path / "base"
    _make_tree(base)

    import builtins
    real_open = builtins.open

    def selective_open(path, mode="r", *args, **kwargs):
        if str(path).endswith("tree.txt") and "w" in mode:
            raise OSError("cannot write tree")
        return real_open(path, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", selective_open)

    out_file = tmp_path / "tree.txt"
    lines = tg.generar_arbol_directorios(
        ruta_base=str(base),
        modo="todo",
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        imprimir=False,
        guardar_archivo=str(out_file),
    )

    assert out_file.exists() is False
    assert any("No se pudo guardar el árbol" in l for l in lines)
    assert any("cannot write tree" in l for l in lines)


def test_render_includes_symbol_lines_when_flags_enabled(tmp_path):
    base = tmp_path / "base"
    base.mkdir(parents=True, exist_ok=True)
    _write(base / "a.py", "def f():\n    return 1\n\nclass K:\n    def m(self):\n        return 2\n")

    lines = tg.generar_arbol_directorios(
        ruta_base=str(base),
        modo="solo_modulos",
        extensiones=[".py"],
        patrones_incluir=[".*"],
        patrones_excluir=tg._default_patrones_excluir(),
        mostrar_funciones=True,
        mostrar_clases=True,
        mostrar_metodos=True,
        imprimir=False,
    )

    assert any("Función: f()" in l for l in lines)
    assert any("Clase: K" in l for l in lines)
    assert any("Método: m()" in l for l in lines)