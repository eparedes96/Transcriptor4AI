# code_transcriptor.py
import os
import re

def transcribir_codigo(
    ruta_base,
    modo="todo",
    extensiones=None,
    patrones_incluir=None,
    patrones_excluir=None,
    archivo_salida="transcripcion",
    output_folder="."
):
    """
    Genera documentos de texto con el contenido de los archivos que cumplan
    con los criterios dados.

    - Si modo es "solo_tests" => genera <archivo_salida>_tests.txt
    - Si modo es "solo_modulos" => genera <archivo_salida>_modulos.txt
    - Si modo es "todo" => genera ambos

    Formato de salida:
      CODIGO:
      -------------------------------------------------------------------------------- (200 guiones)
      <ruta_relativa>
      <contenido_del_archivo>
      ...
    """
    if extensiones is None:
        extensiones = [".py"]
    if patrones_incluir is None:
        patrones_incluir = [".*"]
    if patrones_excluir is None:
        # Se incluyen ahora patrones para .git, .idea y _pycache_
        patrones_excluir = ["^__init__\\.py$", ".*\\.pyc$", "^(\\.git|\\.idea|_pycache_)", "^\\."]

    # Normalizamos la ruta base
    ruta_base = os.path.abspath(ruta_base)

    # Determinamos qué salidas debemos generar
    generar_tests = (modo == "solo_tests" or modo == "todo")
    generar_modulos = (modo == "solo_modulos" or modo == "todo")

    # Nombres de salida (se crean en la carpeta de salida)
    path_tests = os.path.join(output_folder, f"{archivo_salida}_tests.txt")
    path_modulos = os.path.join(output_folder, f"{archivo_salida}_modulos.txt")

    # Inicializamos archivos de salida (sobrescribiendo contenido previo)
    if generar_tests:
        with open(path_tests, "w", encoding="utf-8") as f:
            f.write("CODIGO:\n")
    if generar_modulos:
        with open(path_modulos, "w", encoding="utf-8") as f:
            f.write("CODIGO:\n")

    def es_test(file_name):
        # Se considera test si:
        # - empieza con 'test_'  O  termina con '_test.py'
        pattern = r'^test_.*|.*_test\.py$'
        return re.match(pattern, file_name) is not None

    for root, dirs, files in os.walk(ruta_base):
        # Excluir directorios que coincidan con los patrones de exclusión
        dirs[:] = [d for d in dirs if not any(re.match(px, d) for px in patrones_excluir)]
        for file_name in files:
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, ruta_base)

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

            archivo_es_test = es_test(file_name)

            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except:
                continue

            if archivo_es_test and generar_tests:
                with open(path_tests, "a", encoding="utf-8") as out:
                    out.write("-" * 200 + "\n")
                    out.write(f"{rel_path}\n")
                    out.write(contenido + "\n")

            if not archivo_es_test and generar_modulos:
                with open(path_modulos, "a", encoding="utf-8") as out:
                    out.write("-" * 200 + "\n")
                    out.write(f"{rel_path}\n")
                    out.write(contenido + "\n")
