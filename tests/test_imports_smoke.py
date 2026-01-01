# tests/test_imports_smoke.py
# -----------------------------------------------------------------------------
# Smoke tests for imports and basic "contract" between main.py and app_core.py.
#
# Goals:
# - Ensure app_core is importable in any environment.
# - Ensure main.py is importable when PySimpleGUI is available.
# - Validate app_core exposes the expected public API used by main.py.
# -----------------------------------------------------------------------------

from __future__ import annotations

import importlib.util
import sys

import pytest

import app_core as core


def test_app_core_importable():
    assert core is not None


def test_app_core_public_api_contract():
    required = [
        "CONFIG_FILE",
        "DEFAULT_OUTPUT_SUBDIR",
        "DEFAULT_OUTPUT_PREFIX",
        "cargar_configuracion_por_defecto",
        "cargar_configuracion",
        "guardar_configuracion",
        "normalizar_dir",
        "ruta_salida_real",
        "archivos_destino",
        "existen_ficheros_destino",
    ]
    for name in required:
        assert hasattr(core, name), f"app_core missing: {name}"


def test_main_importable_if_pysimplegui_available():
    """
    main.py depends on PySimpleGUI. If it's not installed, skip.
    """
    if importlib.util.find_spec("PySimpleGUI") is None:
        pytest.skip("PySimpleGUI not installed; skipping main import smoke test.")

    import main  # noqa: F401
    assert "main" in sys.modules