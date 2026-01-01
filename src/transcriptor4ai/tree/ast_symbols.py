from __future__ import annotations

import ast
import os
from typing import List

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
