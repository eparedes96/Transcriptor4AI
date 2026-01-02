# tests/conftest.py
import sys
import os
import pytest

# -----------------------------------------------------------------------------
# Path Configuration
# -----------------------------------------------------------------------------
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

@pytest.fixture
def mock_config_dict():
    """Returns a valid, complete configuration dictionary for testing."""
    return {
        "ruta_carpetas": "/tmp/test",
        "output_base_dir": "/tmp/test",
        "output_subdir_name": "transcript",
        "output_prefix": "test_output",
        "modo_procesamiento": "todo",
        "extensiones": [".py"],
        "patrones_incluir": [".*"],
        "patrones_excluir": [],
        "mostrar_funciones": False,
        "mostrar_clases": False,
        "mostrar_metodos": False,
        "generar_arbol": False,
        "imprimir_arbol": False,
        "guardar_log_errores": True
    }