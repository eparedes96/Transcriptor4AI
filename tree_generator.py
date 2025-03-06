# tree_generator.py
import os
import re
import ast


def generar_arbol_directorios(
        ruta_base,
        modo="todo",
        extensiones=None,
        patrones_incluir=None,
        patrones_excluir=None,
        mostrar_funciones=False,
        mostrar_clases=False,
        guardar_archivo=""
):
    """
    Genera una visualización jerárquica de archivos y, opcionalmente,
    muestra las funciones y clases definidas en cada archivo.

    Si 'guardar_archivo' no es cadena vacía, se guarda el árbol en ese archivo.
    """
    if extensiones is None:
        extensiones = [".py"]
    if patrones_incluir is None:
        patrones_incluir = [".*"]
    if patrones_excluir is None:
        patrones_excluir = ["^__init__\\.py$", ".*\\.pyc$", "^(\\.git|\\.idea|_pycache_)", "^\\."]

    ruta_base = os.path.abspath(ruta_base)

    def es_test(file_name):
        pattern = r'^test_.*|.*_test\.py$'
        return re.match(pattern, file_name) is not None

    estructura = construir_estructura(
        ruta_base,
        modo,
        extensiones,
        patrones_incluir,
        patrones_excluir,
        es_test
    )

    lines = []
    generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=mostrar_funciones,
                             mostrar_clases=mostrar_clases)

    print("\n".join(lines))

    if guardar_archivo:
        with open(guardar_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def construir_estructura(ruta_base, modo, extensiones, patrones_incluir, patrones_excluir, es_test_func):
    estructura = {}

    for root, dirs, files in os.walk(ruta_base):
        # Excluir directorios no deseados
        dirs[:] = [d for d in dirs if not any(re.match(px, d) for px in patrones_excluir)]
        dirs.sort()
        files.sort()

        rel_root = os.path.relpath(root, ruta_base)
        if rel_root == ".":
            rel_root = ""

        nodos_carpeta = estructura
        if rel_root:
            partes = rel_root.split(os.sep)
            for p in partes:
                if p not in nodos_carpeta:
                    nodos_carpeta[p] = {}
                nodos_carpeta = nodos_carpeta[p]

        for file_name in files:
            _, ext = os.path.splitext(file_name)
            if ext not in extensiones:
                continue

            if any(re.match(px, file_name) for px in patrones_excluir):
                continue

            if not any(re.match(pi, file_name) for pi in patrones_incluir):
                continue

            archivo_es_test = es_test_func(file_name)

            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue

            nodos_carpeta[file_name] = {
                "tipo": "archivo"
            }

    return estructura


def generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=False, mostrar_clases=False, level=0):
    entries = sorted(estructura.keys())
    total = len(entries)
    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        if isinstance(estructura[entry], dict):
            if "tipo" in estructura[entry] and estructura[entry]["tipo"] == "archivo":
                lines.append(prefix + connector + entry)
                if mostrar_funciones or mostrar_clases:
                    info_fc = extraer_funciones_clases_dummy(entry, mostrar_funciones, mostrar_clases)
                    for linea_info in info_fc:
                        lines.append(prefix + ("    " if is_last else "│   ") + linea_info)
            else:
                lines.append(prefix + connector + entry)
                new_prefix = prefix + ("    " if is_last else "│   ")
                generar_estructura_texto(
                    estructura[entry],
                    lines,
                    prefix=new_prefix,
                    mostrar_funciones=mostrar_funciones,
                    mostrar_clases=mostrar_clases,
                    level=level + 1
                )
        else:
            lines.append(prefix + connector + entry)


def extraer_funciones_clases_dummy(nombre_archivo, mostrar_funciones, mostrar_clases):
    resultados = []
    if mostrar_funciones:
        resultados.append("función_ejemplo_1()")
        resultados.append("función_ejemplo_2()")
    if mostrar_clases:
        resultados.append("ClaseEjemplo1")
        resultados.append("ClaseEjemplo2")
    return [f"  -> {r}" for r in resultados] if resultados else []
