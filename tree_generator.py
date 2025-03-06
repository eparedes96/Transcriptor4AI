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
        guardar_archivo=None
):
    """
    Genera una visualización jerárquica de archivos y (opcionalmente) muestra
    las funciones y clases definidas en cada archivo.

    Si 'guardar_archivo' no es None o cadena vacía, se guarda el árbol en ese archivo.
    """
    if extensiones is None:
        extensiones = [".py"]
    if patrones_incluir is None:
        patrones_incluir = [".*"]
    if patrones_excluir is None:
        patrones_excluir = ["^__init__\\.py$", ".*\\.pyc$", "^\\."]

    ruta_base = os.path.abspath(ruta_base)

    # Función para saber si un archivo es test o no
    def es_test(file_name):
        pattern = r'^test_.*|.*_test\.py$'
        return re.match(pattern, file_name) is not None

    # Recolectamos la estructura de directorios en memoria
    estructura = construir_estructura(
        ruta_base,
        modo,
        extensiones,
        patrones_incluir,
        patrones_excluir,
        es_test
    )

    # Generamos la representación en texto (árbol jerárquico)
    lines = []
    generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=mostrar_funciones,
                             mostrar_clases=mostrar_clases)

    # Mostramos en consola
    print("\n".join(lines))

    # Guardamos en archivo si aplica
    if guardar_archivo:
        with open(guardar_archivo, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


def construir_estructura(ruta_base, modo, extensiones, patrones_incluir, patrones_excluir, es_test_func):
    """
    Devuelve una estructura de datos (diccionario anidado) que representa
    la jerarquía de directorios y archivos a partir de una ruta base.
    """
    estructura = {}

    for root, dirs, files in os.walk(ruta_base):
        # Ordenamos las carpetas y archivos por nombre para una salida consistente
        dirs.sort()
        files.sort()

        # Filtramos las carpetas ocultas si se desea. (aquí no se excluyen,
        # pero podrías hacerlo: dirs[:] = [d for d in dirs if not d.startswith('.')])
        rel_root = os.path.relpath(root, ruta_base)
        if rel_root == ".":
            rel_root = ""  # Para la carpeta raíz

        # Nos aseguramos de tener un dict donde guardar la info
        nodos_carpeta = estructura
        if rel_root:
            partes = rel_root.split(os.sep)
            for p in partes:
                if p not in nodos_carpeta:
                    nodos_carpeta[p] = {}
                nodos_carpeta = nodos_carpeta[p]

        for file_name in files:
            # 1) Comprobamos la extensión
            _, ext = os.path.splitext(file_name)
            if ext not in extensiones:
                continue

            # 2) Verificamos patrones de exclusión
            if any(re.match(px, file_name) for px in patrones_excluir):
                continue

            # 3) Verificamos patrones de inclusión
            if not any(re.match(pi, file_name) for pi in patrones_incluir):
                continue

            # 4) Determinamos si es test o módulo
            archivo_es_test = es_test_func(file_name)

            # 5) Aplicamos el 'modo'
            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue
            # modo == "todo" => no discriminamos

            # Guardamos un marcador del archivo
            nodos_carpeta[file_name] = {
                "tipo": "archivo"
            }

    return estructura


def generar_estructura_texto(estructura, lines, prefix="", mostrar_funciones=False, mostrar_clases=False, level=0):
    """
    Convierte el diccionario `estructura` (carpetas y archivos) en líneas de texto
    con formato de árbol jerárquico. Además, si se solicita, analiza las funciones
    y clases de los archivos .py.
    """
    # Extraemos las keys en orden alfabético
    entries = sorted(estructura.keys())
    total = len(entries)
    for i, entry in enumerate(entries):
        is_last = (i == total - 1)
        connector = "└── " if is_last else "├── "

        if isinstance(estructura[entry], dict):
            # Es una carpeta (o un archivo .py con datos anidados, en caso extraño)
            # Comprobamos si es realmente un archivo, o una carpeta
            # Si "tipo" no está, entendemos que es carpeta
            if "tipo" in estructura[entry] and estructura[entry]["tipo"] == "archivo":
                # Es un archivo
                lines.append(prefix + connector + entry)
                # ¿Mostramos funciones/clases?
                if mostrar_funciones or mostrar_clases:
                    # path ficticio, no podemos reconstruir con exactitud la absoluta,
                    # a menos que guardáramos la ruta completa. Para demostración:
                    # lines += [prefix + "    (ejemplo de funciones/clases)"]
                    ruta_absoluta = "No disponible"  # Podrías guardar la ruta real en `construir_estructura`
                    info_fc = extraer_funciones_clases_dummy(entry, mostrar_funciones, mostrar_clases)
                    for linea_info in info_fc:
                        lines.append(prefix + ("    " if is_last else "│   ") + linea_info)
            else:
                # Es un directorio
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
            # Caso raro (debería ser dict si es carpeta/archivo)
            lines.append(prefix + connector + entry)


def extraer_funciones_clases_dummy(nombre_archivo, mostrar_funciones, mostrar_clases):
    """
    Función de ejemplo para 'mostrar' supuestas clases/funciones.
    En un escenario real, abrirías el archivo, parsearías con 'ast' y extraerías
    la lista de definiciones.
    """
    resultados = []
    if mostrar_funciones:
        # Aquí podrías mostrar: "funcion: <nombre>" por cada función
        resultados.append("función_ejemplo_1()")
        resultados.append("función_ejemplo_2()")

    if mostrar_clases:
        # Aquí podrías mostrar: "clase: <nombre>" por cada clase
        resultados.append("ClaseEjemplo1")
        resultados.append("ClaseEjemplo2")

    if not resultados:
        return []
    # Prependimos algo para mayor claridad
    return [f"  -> {r}" for r in resultados]
