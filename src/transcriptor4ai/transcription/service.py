from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from transcriptor4ai.filtering import (
    compile_patterns,
    default_extensiones,
    default_exclude_patterns,
    default_include_patterns,
    es_test,
    matches_any,
    matches_include,
)
from transcriptor4ai.paths import _safe_mkdir
from transcriptor4ai.transcription.format import _append_entry
from transcriptor4ai.transcription.models import TranscriptionError

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def transcribe_code(
        ruta_base: str,
        modo: str = "todo",
        extensiones: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        archivo_salida: str = "transcripcion",
        output_folder: str = ".",
        save_error_log: bool = True,
) -> Dict[str, Any]:
    """
    Consolidate source code into text files based on filtering criteria.

    Generates:
      - {prefix}_tests.txt
      - {prefix}_modulos.txt
      - {prefix}_errores.txt (optional)

    Args:
        ruta_base: Source directory.
        modo: "todo", "solo_modulos", "solo_tests".
        extensiones: List of file extensions to process.
        include_patterns: Whitelist regex patterns.
        exclude_patterns: Blacklist regex patterns.
        archivo_salida: Prefix for output files.
        output_folder: Destination directory.
        save_error_log: Whether to write a separate error log file.

    Returns:
        A dictionary containing counters, paths, and status.
    """
    logger.info(f"Starting transcription scan in: {ruta_base}")

    # -------------------------
    # Input Normalization
    # -------------------------
    if extensiones is None:
        extensiones = default_extensiones()
    if include_patterns is None:
        include_patterns = default_include_patterns()
    if exclude_patterns is None:
        exclude_patterns = default_exclude_patterns()

    ruta_base_abs = os.path.abspath(ruta_base)
    output_folder_abs = os.path.abspath(output_folder)

    incluir_rx = compile_patterns(include_patterns)
    excluir_rx = compile_patterns(exclude_patterns)

    generar_tests = (modo == "solo_tests" or modo == "todo")
    generar_modulos = (modo == "solo_modulos" or modo == "todo")

    # -------------------------
    # Prepare Output Directory
    # -------------------------
    ok, err = _safe_mkdir(output_folder_abs)
    if not ok:
        logger.error(f"Failed to create output directory: {err}")
        return {
            "ok": False,
            "error": f"Output directory error '{output_folder_abs}': {err}",
            "output_folder": output_folder_abs,
        }

    path_tests = os.path.join(output_folder_abs, f"{archivo_salida}_tests.txt")
    path_modulos = os.path.join(output_folder_abs, f"{archivo_salida}_modulos.txt")
    path_errores = os.path.join(output_folder_abs, f"{archivo_salida}_errores.txt")

    # Initialize files with headers
    try:
        if generar_tests:
            with open(path_tests, "w", encoding="utf-8") as f:
                f.write("CODIGO:\n")
        if generar_modulos:
            with open(path_modulos, "w", encoding="utf-8") as f:
                f.write("CODIGO:\n")
    except OSError as e:
        logger.error(f"Failed to initialize output files: {e}")
        return {
            "ok": False,
            "error": f"Output initialization error: {e}",
            "output_folder": output_folder_abs,
        }

    # -------------------------
    # Filesystem Traversal
    # -------------------------
    errores: List[TranscriptionError] = []
    procesados = 0
    omitidos = 0
    escritos_tests = 0
    escritos_modulos = 0

    for root, dirs, files in os.walk(ruta_base_abs):
        # Prune excluded directories
        dirs[:] = [d for d in dirs if not matches_any(d, excluir_rx)]
        dirs.sort()
        files.sort()

        for file_name in files:
            _, ext = os.path.splitext(file_name)

            # --- Filtering ---
            if ext not in extensiones:
                omitidos += 1
                continue

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

            # --- Processing ---
            file_path = os.path.join(root, file_name)
            rel_path = os.path.relpath(file_path, ruta_base_abs)

            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    contenido = f.read()
            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Error reading file {rel_path}: {e}")
                errores.append(TranscriptionError(rel_path=rel_path, error=str(e)))
                continue

            try:
                if archivo_es_test and generar_tests:
                    _append_entry(path_tests, rel_path, contenido)
                    escritos_tests += 1
                if (not archivo_es_test) and generar_modulos:
                    _append_entry(path_modulos, rel_path, contenido)
                    escritos_modulos += 1

                procesados += 1
                # Optional: Verbose logging for every file might be too noisy,
                # so we stick to debug or omit it unless necessary.
                logger.debug(f"Processed: {rel_path}")

            except OSError as e:
                msg = f"Error writing to output: {e}"
                logger.error(msg)
                errores.append(TranscriptionError(rel_path=rel_path, error=msg))
                continue

    # -------------------------
    # Error Logging
    # -------------------------
    if save_error_log and errores:
        try:
            with open(path_errores, "w", encoding="utf-8") as f:
                f.write("ERRORES:\n")
                for err_item in errores:
                    f.write("-" * 80 + "\n")
                    f.write(f"{err_item.rel_path}\n")
                    f.write(f"{err_item.error}\n")
            logger.info(f"Error log saved to: {path_errores}")
        except OSError as e:
            logger.error(f"Failed to save error log: {e}")

    logger.info(
        f"Transcription finished. Processed: {procesados}, "
        f"Tests: {escritos_tests}, Modules: {escritos_modulos}, Errors: {len(errores)}"
    )

    # -------------------------
    # Result Construction
    # -------------------------
    result = {
        "ok": True,
        "ruta_base": ruta_base_abs,
        "output_folder": output_folder_abs,
        "modo": modo,
        "generados": {
            "tests": path_tests if generar_tests else "",
            "modulos": path_modulos if generar_modulos else "",
            "errores": path_errores if (save_error_log and errores) else (
                path_errores if save_error_log else ""),
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