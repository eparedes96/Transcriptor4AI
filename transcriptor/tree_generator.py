# tree_generator.py
# -----------------------------------------------------------------------------
# Generador de árbol de directorios + extracción opcional de funciones/clases.
# -----------------------------------------------------------------------------

from __future__ import annotations

import os
import re
import ast
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Union


# -----------------------------------------------------------------------------
# Utilidades y configuración
# -----------------------------------------------------------------------------

def _default_extensiones() -> List[str]:
    return [".py"]


def _default_patrones_incluir() -> List[str]:
    return [".*"]


def _default_patrones_excluir() -> List[str]:
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
        r"^\."  # ocultos: .venv, .mypy_cache, etc.
    ]


def _compile_patterns(patterns: List[str]) -> List[re.Pattern]:
    compiled: List[re.Pattern] = []
    for p in patterns:
        try:
            compiled.append(re.compile(p))
        except re.error as e:
            continue
    return compiled


def _matches_any(name: str, compiled_patterns: List[re.Pattern]) -> bool:
    return any(rx.match(name) for rx in compiled_patterns)


def _es_test(file_name: str) -> bool:
    """
    Detecta ficheros de test tipo:
      - test_algo.py
      - algo_test.py
    """
    return re.match(r"^(test_.*\.py|.*_test\.py)$", file_name) is not None


# -----------------------------------------------------------------------------
# Modelo de datos
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class FileNode:
    path: str


Tree = Dict[str, Union["Tree", FileNode]]


# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------

def generar_arbol_directorios(
    ruta_base: str,
    modo: str = "todo",
    extensiones: Optional[List[str]] = None,
    patrones_incluir: Optional[List[str]] = None,
    patrones_excluir: Optional[List[str]] = None,
    mostrar_funciones: bool = False,
    mostrar_clases: bool = False,
    mostrar_metodos: bool = False,
    imprimir: bool = True,
    guardar_archivo: str = "",
) -> List[str]:
    """
    Genera una visualización jerárquica de archivos y, opcionalmente, muestra
    símbolos del archivo (funciones/clases, y opcionalmente métodos de clase).

    - modo: "all" | "only_modules" | "only_test"
    - imprimir: si True imprime en consola
    - guardar_archivo: si se proporciona, guarda el árbol en ese fichero

    Devuelve:
      Lista de líneas (strings) del árbol generado (útil para GUI / tests).
    """
    # -------------------------
    # Normalización de inputs
    # -------------------------
    if extensiones is None:
        extensiones = _default_extensiones()
    if patrones_incluir is None:
        patrones_incluir = _default_patrones_incluir()
    if patrones_excluir is None:
        patrones_excluir = _default_patrones_excluir()

    ruta_base_abs = os.path.abspath(ruta_base)

    incluir_rx = _compile_patterns(patrones_incluir)
    excluir_rx = _compile_patterns(patrones_excluir)

    # -------------------------
    # Construcción de estructura
    # -------------------------
    estructura = construir_estructura(
        ruta_base_abs,
        modo=modo,
        extensiones=extensiones,
        incluir_rx=incluir_rx,
        excluir_rx=excluir_rx,
        es_test_func=_es_test,
    )

    # -------------------------
    # Renderizado del árbol
    # -------------------------
    lines: List[str] = []
    generar_estructura_texto(
        estructura,
        lines,
        prefix="",
        mostrar_funciones=mostrar_funciones,
        mostrar_clases=mostrar_clases,
        mostrar_metodos=mostrar_metodos,
    )

    # -------------------------
    # Salida (consola / fichero)
    # -------------------------
    if imprimir:
        print("\n".join(lines))

    if guardar_archivo:
        try:
            out_dir = os.path.dirname(os.path.abspath(guardar_archivo))
            if out_dir and not os.path.exists(out_dir):
                os.makedirs(out_dir, exist_ok=True)

            with open(guardar_archivo, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")
        except OSError as e:
            lines.append(f"[ERROR] No se pudo guardar el árbol en '{guardar_archivo}': {e}")

    return lines


# -----------------------------------------------------------------------------
# Construcción de estructura
# -----------------------------------------------------------------------------

def construir_estructura(
    ruta_base: str,
    modo: str,
    extensiones: List[str],
    incluir_rx: List[re.Pattern],
    excluir_rx: List[re.Pattern],
    es_test_func: Callable[[str], bool],
) -> Tree:
    estructura: Tree = {}

    for root, dirs, files in os.walk(ruta_base):
        dirs[:] = [d for d in dirs if not _matches_any(d, excluir_rx)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, ruta_base)
        if rel_root == ".":
            rel_root = ""

        # Navegar/crear nodos intermedios
        nodos_carpeta: Tree = estructura
        if rel_root:
            for p in rel_root.split(os.sep):
                if p not in nodos_carpeta or not isinstance(nodos_carpeta[p], dict):
                    nodos_carpeta[p] = {}
                nodos_carpeta = nodos_carpeta[p]

        # Procesar archivos
        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext not in extensiones:
                continue

            # Excluir/incluir por patrones (aplicados sobre nombre del archivo)
            if _matches_any(file_name, excluir_rx):
                continue
            if not any(rx.match(file_name) for rx in incluir_rx):
                continue

            archivo_es_test = es_test_func(file_name)
            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue

            # Guardar nodo archivo
            full_path = os.path.join(root, file_name)
            nodos_carpeta[file_name] = FileNode(path=full_path)

    return estructura


# -----------------------------------------------------------------------------
# Render del árbol
# -----------------------------------------------------------------------------

def generar_estructura_texto(
    estructura: Tree,
    lines: List[str],
    prefix: str = "",
    mostrar_funciones: bool = False,
    mostrar_clases: bool = False,
    mostrar_metodos: bool = False,
) -> None:
    entries = sorted(estructura.keys())
    total = len(entries)

    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "
        node = estructura[entry]

        # Directorio (subárbol)
        if isinstance(node, dict):
            lines.append(prefix + connector + entry)
            new_prefix = prefix + ("    " if is_last else "│   ")
            generar_estructura_texto(
                node,
                lines,
                prefix=new_prefix,
                mostrar_funciones=mostrar_funciones,
                mostrar_clases=mostrar_clases,
                mostrar_metodos=mostrar_metodos,
            )
            continue

        # Archivo
        if isinstance(node, FileNode):
            lines.append(prefix + connector + entry)

            if mostrar_funciones or mostrar_clases or mostrar_metodos:
                info_fc = extraer_funciones_clases(
                    node.path,
                    mostrar_funciones=mostrar_funciones,
                    mostrar_clases=mostrar_clases,
                    mostrar_metodos=mostrar_metodos,
                )
                child_prefix = prefix + ("    " if is_last else "│   ")
                for linea_info in info_fc:
                    lines.append(child_prefix + linea_info)

            continue

        # Fallback
        lines.append(prefix + connector + entry)


# -----------------------------------------------------------------------------
# Extracción AST (símbolos)
# -----------------------------------------------------------------------------

def extraer_funciones_clases(
    file_path: str,
    mostrar_funciones: bool,
    mostrar_clases: bool,
    mostrar_metodos: bool = False,
) -> List[str]:
    """
    Extrae definiciones del archivo usando AST.

    - mostrar_funciones: funciones de nivel superior
    - mostrar_clases: clases de nivel superior
    - mostrar_metodos: si True y mostrar_clases True, lista métodos de esas clases

    Devuelve una lista de líneas ya formateadas para insertarlas en el árbol.
    """
    resultados: List[str] = []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            source = f.read()
    except (OSError, UnicodeDecodeError) as e:
        return [f"[ERROR] No se pudo leer '{os.path.basename(file_path)}': {e}"]

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        return [f"[ERROR] AST inválido (SyntaxError): {e.msg} (línea {e.lineno})"]
    except Exception as e:
        return [f"[ERROR] Error al parsear AST: {e}"]

    # Nivel superior
    for node in tree.body:
        if mostrar_funciones and isinstance(node, ast.FunctionDef):
            resultados.append(f"Función: {node.name}()")
        if mostrar_clases and isinstance(node, ast.ClassDef):
            resultados.append(f"Clase: {node.name}")

            if mostrar_metodos:
                metodos = []
                for child in node.body:
                    if isinstance(child, ast.FunctionDef):
                        metodos.append(child.name)
                for m in metodos:
                    resultados.append(f"  Método: {m}()")

    return resultados