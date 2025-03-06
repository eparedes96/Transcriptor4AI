# code_transcriptor.py
import os
import re


def transcribir_codigo(
        ruta_base,
        modo="todo",
        extensiones=None,
        patrones_incluir=None,
        patrones_excluir=None,
        archivo_salida="transcripcion"
):
    """
    Genera documentos de texto con el contenido de los archivos que cumplan
    con los criterios dados (modo, extensiones, patrones de inclusión/exclusión, etc.).

    - Si modo es "solo_tests" => genera <archivo_salida>_tests.txt
    - Si modo es "solo_modulos" => genera <archivo_salida>_modulos.txt
    - Si modo es "todo" => genera ambos: <archivo_salida>_tests.txt y <archivo_salida>_modulos.txt

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
        patrones_excluir = ["^__init__\\.py$", ".*\\.pyc$", "^\\."]

    # Normalizamos la ruta base
    ruta_base = os.path.abspath(ruta_base)

    # Determinamos qué salidas debemos generar
    generar_tests = (modo == "solo_tests" or modo == "todo")
    generar_modulos = (modo == "solo_modulos" or modo == "todo")

    # Nombres de salida
    path_tests = f"{archivo_salida}_tests.txt"
    path_modulos = f"{archivo_salida}_modulos.txt"

    # Inicializamos archivos de salida, si corresponde
    # El modo "w" sobreescribe el contenido previo
    if generar_tests:
        with open(path_tests, "w", encoding="utf-8") as f:
            f.write("CODIGO:\n")
    if generar_modulos:
        with open(path_modulos, "w", encoding="utf-8") as f:
            f.write("CODIGO:\n")

    # Función para saber si un archivo es de test o no
    # (Podrías ajustar la lógica/patrones según tus necesidades)
    def es_test(file_name):
        # Se considera test si:
        # - empieza con 'test_'  O  termina con '_test.py'
        base = os.path.basename(file_name)
        pattern = r'^test_.*|.*_test\.py$'
        return re.match(pattern, base) is not None

    for root, dirs, files in os.walk(ruta_base):
        # Excluimos carpetas ocultas si aplica el patrón_excluir de '^\.'
        # (Si quisieras excluir directorios con '.' podrías filtrar 'dirs' aquí)
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

            # 4) Determinamos si es test o módulo
            archivo_es_test = es_test(file_name)

            # 5) Aplicamos el 'modo' para decidir si lo procesamos
            if modo == "solo_tests" and not archivo_es_test:
                continue
            if modo == "solo_modulos" and archivo_es_test:
                continue
            # Si es "todo" procesamos siempre, no discriminamos

            # Leemos el contenido del archivo
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except:
                # Si no se puede leer (p.e. error de codificación), saltamos
                continue

            # Decidimos en qué archivo de salida se escribe
            # - Si el archivo es test => en tests.txt
            # - Si es un módulo => en modulos.txt
            # - Si modo=todo => ambos (test va a tests, módulo va a modulos)
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
