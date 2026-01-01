from __future__ import annotations

import os
from typing import Optional, List

from transcriptor4ai.filtering import (
    default_extensiones,
    default_patrones_incluir,
    default_patrones_excluir,
    compile_patterns,
    matches_any,
    matches_include,
    es_test,
)
from transcriptor4ai.transcription.models import TranscriptionError
from transcriptor4ai.transcription.format import _append_entry
from transcriptor4ai.paths import _safe_mkdir

# -----------------------------------------------------------------------------
# API pública
# -----------------------------------------------------------------------------
def transcribir_codigo(
    ruta_base: str,
    modo: str = "todo",
    extensiones: Optional[List[str]] = None,
    patrones_incluir: Optional[List[str]] = None,
    patrones_excluir: Optional[List[str]] = None,
    archivo_salida: str = "transcripcion",
    output_folder: str = ".",
    guardar_log_errores: bool = True,
) -> dict:
    """
    Genera documentos de texto con el contenido de los archivos que cumplan
    con los criterios dados.

    - Si modo es "only_test" => genera <prefijo>_tests.txt
    - Si modo es "only_modules" => genera <prefijo>_modulos.txt
    - Si modo es "all" => genera ambos

    Formato de salida por archivo:
      CODIGO:
      -------------------------------------------------------------------------------- (200 guiones)
      <ruta_relativa>
      <contenido_del_archivo>

    Devuelve un dict con contadores y rutas generadas, útil para GUI/tests.
    """
    # -------------------------
    # Normalización de inputs
    # -------------------------
    if extensiones is None:
        extensiones = default_extensiones()
    if patrones_incluir is None:
        patrones_incluir = default_patrones_incluir()
    if patrones_excluir is None:
        patrones_excluir = default_patrones_excluir()

    ruta_base_abs = os.path.abspath(ruta_base)
    output_folder_abs = os.path.abspath(output_folder)

    incluir_rx = compile_patterns(patrones_incluir)
    excluir_rx = compile_patterns(patrones_excluir)

    generar_tests = (modo == "solo_tests" or modo == "todo")
    generar_modulos = (modo == "solo_modulos" or modo == "todo")

    # -------------------------
    # Preparación de salida
    # -------------------------
    ok, err = _safe_mkdir(output_folder_abs)
    if not ok:
        return {
            "ok": False,
            "error": f"No se pudo crear/usar la carpeta de salida '{output_folder_abs}': {err}",
            "output_folder": output_folder_abs,
        }

    path_tests = os.path.join(output_folder_abs, f"{archivo_salida}_tests.txt")
    path_modulos = os.path.join(output_folder_abs, f"{archivo_salida}_modulos.txt")
    path_errores = os.path.join(output_folder_abs, f"{archivo_salida}_errores.txt")

    # Escribimos cabecera inicial
    try:
        if generar_tests:
            with open(path_tests, "w", encoding="utf-8") as f:
                f.write("CODIGO:\n")
        if generar_modulos:
            with open(path_modulos, "w", encoding="utf-8") as f:
                f.write("CODIGO:\n")
    except OSError as e:
        return {
            "ok": False,
            "error": f"No se pudieron inicializar los archivos de salida: {e}",
            "output_folder": output_folder_abs,
        }

    # -------------------------
    # Recorrido del filesystem
    # -------------------------
    errores: List[TranscriptionError] = []
    procesados = 0
    omitidos = 0
    escritos_tests = 0
    escritos_modulos = 0

    for root, dirs, files in os.walk(ruta_base_abs):
        dirs[:] = [d for d in dirs if not matches_any(d, excluir_rx)]
        dirs.sort()
        files.sort()

        for file_name in files:
            _, ext = os.path.splitext(file_name)

            # Filtrar extensión
            if ext not in extensiones:
                omitidos += 1
                continue

            # Excluir / incluir por patrones en nombre de archivo
            if matches_any(file_name, excluir_rx):
                omitidos += 1
                continue
            if not matches_include(file_name, incluir_rx):
                omitidos += 1
                continue

            archivo_es_test = es_test(file_name)
            if modo == "solo_tests" and not archivo_es_test:
                omitidos += 1
                continue
            if modo == "solo_modulos" and archivo_es_test:
                omitidos += 1
                continue

            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, ruta_base_abs)

            # Leer contenido
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except (OSError, UnicodeDecodeError) as e:
                errores.append(TranscriptionError(rel_path=rel_path, error=str(e)))
                continue

            # Escribir a salida correspondiente
            try:
                if archivo_es_test and generar_tests:
                    _append_entry(path_tests, rel_path, contenido)
                    escritos_tests += 1
                if (not archivo_es_test) and generar_modulos:
                    _append_entry(path_modulos, rel_path, contenido)
                    escritos_modulos += 1
                procesados += 1
            except OSError as e:
                errores.append(TranscriptionError(rel_path=rel_path, error=f"Error escribiendo salida: {e}"))
                continue

    # -------------------------
    # Log de errores
    # -------------------------
    if guardar_log_errores:
        try:
            with open(path_errores, "w", encoding="utf-8") as f:
                f.write("ERRORES:\n")
                for err_item in errores:
                    f.write("-" * 80 + "\n")
                    f.write(f"{err_item.rel_path}\n")
                    f.write(f"{err_item.error}\n")
        except OSError:
            pass

    # -------------------------
    # Resultado para el caller
    # -------------------------
    result = {
        "ok": True,
        "ruta_base": ruta_base_abs,
        "output_folder": output_folder_abs,
        "modo": modo,
        "generados": {
            "tests": path_tests if generar_tests else "",
            "modulos": path_modulos if generar_modulos else "",
            "errores": path_errores if (guardar_log_errores and errores) else (path_errores if guardar_log_errores else ""),
        },
        "contadores": {
            "procesados": procesados,
            "omitidos": omitidos,
            "tests_escritos": escritos_tests,
            "modulos_escritos": escritos_modulos,
            "errores": len(errores),
        },
    }
    return result