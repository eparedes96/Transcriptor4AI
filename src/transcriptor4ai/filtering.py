from __future__ import annotations

import re
from typing import List

# -----------------------------------------------------------------------------
# Configuración por defecto y utilidades
# -----------------------------------------------------------------------------
def default_extensiones() -> List[str]:
    return [".py"]


def default_patrones_incluir() -> List[str]:
    return [".*"]


def default_patrones_excluir() -> List[str]:
    """
    Nota: estos patrones se aplican con re.match (desde el inicio del string).

    - Archivos:
      - __init__.py
      - *.pyc
    - Directorios:
      - __pycache__
      - .git, .idea
      - cualquier cosa que empiece por "."
    """
    return [
        r"^__init__\.py$",
        r".*\.pyc$",
        r"^(__pycache__|\.git|\.idea)$",
        r"^\.",
    ]


def compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    compiled: List[re.Pattern] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error:
            continue
    return compiled


def matches_any(name: str, compiled_patterns: List[re.Pattern]) -> bool:
    return any(rx.match(name) for rx in compiled_patterns)


def matches_include(name: str, include_patterns: List[re.Pattern]) -> bool:
    if not include_patterns:
        return False
    return any(rx.match(name) for rx in include_patterns)


def es_test(file_name: str) -> bool:
    """
    Detecta ficheros de test tipo:
      - test_algo.py
      - algo_test.py
    """
    return re.match(r"^(test_.*\.py|.*_test\.py)$", file_name) is not None

# -----------------------------------------------------------------------------
# Compatibilidad temporal (API legacy con guión bajo)
# - No duplica lógica: son alias al API público
# -----------------------------------------------------------------------------
_default_extensiones = default_extensiones
_default_patrones_incluir = default_patrones_incluir
_default_patrones_excluir = default_patrones_excluir
_compile_patterns = compile_patterns
_matches_any = matches_any
_matches_include = matches_include
_es_test = es_test