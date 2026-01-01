# tests/test_main_helpers_and_config.py
# -----------------------------------------------------------------------------
# Tests for main.py helper functions and config load/save behavior.
# Focus:
# - path normalization helpers
# - output path composition
# - target files list logic
# - detection of existing output files
# - config defaults and persistence (without launching GUI)
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import os
from pathlib import Path

import main as app


# -----------------------------------------------------------------------------
# Helpers: paths
# -----------------------------------------------------------------------------

def test_normalizar_dir_empty_uses_fallback(tmp_path):
    fb = str(tmp_path / "fallback")
    res = app._normalizar_dir("", fb)
    assert os.path.isabs(res)
    assert res.endswith(os.path.basename(fb))


def test_normalizar_dir_expands_user_and_vars(monkeypatch, tmp_path):
    # Use an env var to avoid relying on "~" resolution
    monkeypatch.setenv("XTEST_BASE", str(tmp_path))
    res = app._normalizar_dir("$XTEST_BASE/sub", str(tmp_path))
    assert os.path.isabs(res)
    assert res.endswith(os.path.join(os.path.basename(str(tmp_path)), "sub")) or res.endswith("sub")


def test_ruta_salida_real_uses_default_subdir_when_empty(tmp_path):
    base = str(tmp_path / "base")
    r = app._ruta_salida_real(base, "")
    assert r == os.path.join(base, app.DEFAULT_OUTPUT_SUBDIR)


def test_ruta_salida_real_joins_base_and_subdir(tmp_path):
    base = str(tmp_path / "base")
    r = app._ruta_salida_real(base, "x")
    assert r == os.path.join(base, "x")


def test_archivos_destino_for_each_mode_and_tree_flag():
    # todo + tree => 3
    names = app._archivos_destino("p", "todo", True)
    assert set(names) == {"p_tests.txt", "p_modulos.txt", "p_arbol.txt"}

    # todo no tree => 2
    names = app._archivos_destino("p", "todo", False)
    assert set(names) == {"p_tests.txt", "p_modulos.txt"}

    # solo_modulos => 1 (+tree optional)
    names = app._archivos_destino("p", "solo_modulos", False)
    assert names == ["p_modulos.txt"]
    names = app._archivos_destino("p", "solo_modulos", True)
    assert set(names) == {"p_modulos.txt", "p_arbol.txt"}

    # solo_tests => 1 (+tree optional)
    names = app._archivos_destino("p", "solo_tests", False)
    assert names == ["p_tests.txt"]
    names = app._archivos_destino("p", "solo_tests", True)
    assert set(names) == {"p_tests.txt", "p_arbol.txt"}


def test_existen_ficheros_destino_detects_existing(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "a.txt").write_text("x", encoding="utf-8")
    names = ["a.txt", "b.txt"]

    existentes = app._existen_ficheros_destino(str(out_dir), names)
    assert len(existentes) == 1
    assert existentes[0].endswith(os.path.join("out", "a.txt"))


# -----------------------------------------------------------------------------
# Config: defaults, save/load/merge
# -----------------------------------------------------------------------------

def test_defaults_are_coherent_output_base_equals_input():
    conf = app.cargar_configuracion_por_defecto()
    assert conf["ruta_carpetas"] == conf["output_base_dir"]
    assert conf["output_subdir_name"] == app.DEFAULT_OUTPUT_SUBDIR
    assert conf["output_prefix"] == app.DEFAULT_OUTPUT_PREFIX


def test_guardar_configuracion_writes_valid_json(tmp_path, monkeypatch):
    # isolate config.json by changing cwd
    monkeypatch.chdir(tmp_path)

    conf = app.cargar_configuracion_por_defecto()
    app.guardar_configuracion(conf)

    cfg = tmp_path / app.CONFIG_FILE
    assert cfg.exists()

    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "ruta_carpetas" in data
    assert "output_base_dir" in data


def test_cargar_configuracion_merges_existing_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    base_conf = app.cargar_configuracion_por_defecto()
    # write custom partial config
    custom = {
        "modo_procesamiento": "solo_tests",
        "output_subdir_name": "custom_out",
    }
    Path(app.CONFIG_FILE).write_text(json.dumps(custom), encoding="utf-8")

    conf = app.cargar_configuracion()
    # merged values
    assert conf["modo_procesamiento"] == "solo_tests"
    assert conf["output_subdir_name"] == "custom_out"
    # untouched defaults still exist
    assert conf["output_prefix"] == base_conf["output_prefix"]
    assert "patrones_excluir" in conf


def test_cargar_configuracion_corrupt_json_falls_back_to_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    Path(app.CONFIG_FILE).write_text("{not-json", encoding="utf-8")
    conf = app.cargar_configuracion()

    defaults = app.cargar_configuracion_por_defecto()
    # should match defaults for key fields
    assert conf["modo_procesamiento"] == defaults["modo_procesamiento"]
    assert conf["output_subdir_name"] == defaults["output_subdir_name"]
    assert conf["output_prefix"] == defaults["output_prefix"]