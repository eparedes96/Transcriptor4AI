# tests/test_main_helpers_and_config.py
# -----------------------------------------------------------------------------
# Tests for app_core.py helpers and config load/save behavior.
# Focus:
# - path normalization helpers
# - output path composition
# - target files list logic
# - detection of existing output files
# - config defaults and persistence (without GUI)
# - regression: load old config.json shape (pre-separation)
# -----------------------------------------------------------------------------

from __future__ import annotations

import json
import os
from pathlib import Path

import app_core as app
import transcriptor4ai.config
import transcriptor4ai.paths


# -----------------------------------------------------------------------------
# Helpers: paths
# -----------------------------------------------------------------------------

def test_normalizar_dir_empty_uses_fallback(tmp_path):
    fb = str(tmp_path / "fallback")
    res = transcriptor4ai.paths.normalizar_dir("", fb)
    assert os.path.isabs(res)
    assert res.endswith(os.path.basename(fb))


def test_normalizar_dir_expands_user_and_vars(monkeypatch, tmp_path):
    monkeypatch.setenv("XTEST_BASE", str(tmp_path))
    res = transcriptor4ai.paths.normalizar_dir("$XTEST_BASE/sub", str(tmp_path))
    assert os.path.isabs(res)
    assert res.endswith(os.path.join(os.path.basename(str(tmp_path)), "sub")) or res.endswith("sub")


def test_ruta_salida_real_uses_default_subdir_when_empty(tmp_path):
    base = str(tmp_path / "base")
    r = transcriptor4ai.paths.ruta_salida_real(base, "")
    assert r == os.path.join(base, transcriptor4ai.paths.DEFAULT_OUTPUT_SUBDIR)


def test_ruta_salida_real_joins_base_and_subdir(tmp_path):
    base = str(tmp_path / "base")
    r = transcriptor4ai.paths.ruta_salida_real(base, "x")
    assert r == os.path.join(base, "x")


def test_archivos_destino_for_each_mode_and_tree_flag():
    # all + tree => 3
    names = transcriptor4ai.paths.archivos_destino("p", "todo", True)
    assert set(names) == {"p_tests.txt", "p_modulos.txt", "p_arbol.txt"}

    # all no tree => 2
    names = transcriptor4ai.paths.archivos_destino("p", "todo", False)
    assert set(names) == {"p_tests.txt", "p_modulos.txt"}

    # solo_modulos => 1 (+tree optional)
    names = transcriptor4ai.paths.archivos_destino("p", "solo_modulos", False)
    assert names == ["p_modulos.txt"]
    names = transcriptor4ai.paths.archivos_destino("p", "solo_modulos", True)
    assert set(names) == {"p_modulos.txt", "p_arbol.txt"}

    # solo_tests => 1 (+tree optional)
    names = transcriptor4ai.paths.archivos_destino("p", "solo_tests", False)
    assert names == ["p_tests.txt"]
    names = transcriptor4ai.paths.archivos_destino("p", "solo_tests", True)
    assert set(names) == {"p_tests.txt", "p_arbol.txt"}


def test_existen_ficheros_destino_detects_existing(tmp_path):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    (out_dir / "a.txt").write_text("x", encoding="utf-8")
    names = ["a.txt", "b.txt"]

    existentes = transcriptor4ai.paths.existen_ficheros_destino(str(out_dir), names)
    assert len(existentes) == 1
    assert existentes[0].endswith(os.path.join("out", "a.txt"))


# -----------------------------------------------------------------------------
# Config: defaults, save/load/merge
# -----------------------------------------------------------------------------

def test_defaults_are_coherent_output_base_equals_input():
    conf = transcriptor4ai.config.cargar_configuracion_por_defecto()
    assert conf["ruta_carpetas"] == conf["output_base_dir"]
    assert conf["output_subdir_name"] == transcriptor4ai.paths.DEFAULT_OUTPUT_SUBDIR
    assert conf["output_prefix"] == transcriptor4ai.config.DEFAULT_OUTPUT_PREFIX


def test_guardar_configuracion_writes_valid_json(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    conf = transcriptor4ai.config.cargar_configuracion_por_defecto()
    transcriptor4ai.config.guardar_configuracion(conf)

    cfg = tmp_path / transcriptor4ai.config.CONFIG_FILE
    assert cfg.exists()

    data = json.loads(cfg.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    assert "ruta_carpetas" in data
    assert "output_base_dir" in data


def test_cargar_configuracion_merges_existing_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    base_conf = transcriptor4ai.config.cargar_configuracion_por_defecto()
    custom = {
        "modo_procesamiento": "solo_tests",
        "output_subdir_name": "custom_out",
    }
    Path(transcriptor4ai.config.CONFIG_FILE).write_text(json.dumps(custom), encoding="utf-8")

    conf = transcriptor4ai.config.cargar_configuracion()
    assert conf["modo_procesamiento"] == "solo_tests"
    assert conf["output_subdir_name"] == "custom_out"
    assert conf["output_prefix"] == base_conf["output_prefix"]
    assert "patrones_excluir" in conf


def test_cargar_configuracion_corrupt_json_falls_back_to_defaults(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    Path(transcriptor4ai.config.CONFIG_FILE).write_text("{not-json", encoding="utf-8")
    conf = transcriptor4ai.config.cargar_configuracion()

    defaults = transcriptor4ai.config.cargar_configuracion_por_defecto()
    assert conf["modo_procesamiento"] == defaults["modo_procesamiento"]
    assert conf["output_subdir_name"] == defaults["output_subdir_name"]
    assert conf["output_prefix"] == defaults["output_prefix"]


def test_cargar_configuracion_regression_old_config_shape(tmp_path, monkeypatch):
    """
    Regression: old config.json might contain legacy keys like:
    - carpeta_salida
    - ruta_carpetas
    - modo_procesamiento
    In this project, the new format uses output_base_dir/output_subdir_name/output_prefix.
    Expected behavior: merge should not crash, and defaults should remain valid.
    """
    monkeypatch.chdir(tmp_path)

    legacy = {
        "ruta_carpetas": "C:\\fake\\input",
        "carpeta_salida": "transcripcion",
        "modo_procesamiento": "todo",
    }
    Path(transcriptor4ai.config.CONFIG_FILE).write_text(json.dumps(legacy), encoding="utf-8")

    conf = transcriptor4ai.config.cargar_configuracion()

    # Must still have new keys from defaults
    assert "output_base_dir" in conf
    assert "output_subdir_name" in conf
    assert "output_prefix" in conf

    # Existing known keys should merge
    assert conf["modo_procesamiento"] == "todo"
    assert conf["ruta_carpetas"] == "C:\\fake\\input"