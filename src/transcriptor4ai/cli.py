# src/transcriptor4ai/cli.py
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Optional

from transcriptor4ai.config import cargar_configuracion, cargar_configuracion_por_defecto
from transcriptor4ai.pipeline import run_pipeline


# -----------------------------------------------------------------------------
# CLI: parsing
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transcriptor4ai",
        description=(
            "Transcriptor4AI: transcribe código (tests/módulos) y opcionalmente "
            "genera árbol de directorios con símbolos (funciones/clases/métodos)."
        ),
    )

    # --- Input / Output ------------------------------------------------------
    p.add_argument(
        "-i",
        "--input",
        dest="ruta_carpetas",
        help="Ruta de la carpeta a procesar.",
        default=None,
    )
    p.add_argument(
        "-o",
        "--output-base",
        dest="output_base_dir",
        help="Ruta base de salida (se creará una subcarpeta dentro).",
        default=None,
    )
    p.add_argument(
        "--subdir",
        dest="output_subdir_name",
        help="Nombre de la subcarpeta de salida dentro de --output-base.",
        default=None,
    )
    p.add_argument(
        "--prefix",
        dest="output_prefix",
        help="Prefijo de los ficheros generados (p.ej. transcripcion).",
        default=None,
    )

    # --- Mode / Features -----------------------------------------------------
    p.add_argument(
        "--modo",
        choices=["todo", "solo_modulos", "solo_tests"],
        default=None,
        help="Modo de procesamiento: todo | solo_modulos | solo_tests.",
    )
    p.add_argument(
        "--tree",
        action="store_true",
        help="Generar árbol de directorios (archivo y/o consola según flags).",
    )
    p.add_argument(
        "--tree-file",
        dest="tree_file",
        default=None,
        help="Ruta del fichero donde guardar el árbol. Si se omite, se guarda en la salida estándar del pipeline (prefijo_arbol.txt).",
    )
    p.add_argument(
        "--print-tree",
        action="store_true",
        help="Imprimir el árbol por consola (además de guardarlo si corresponde).",
    )

    # --- AST flags -----------------------------------------------------------
    p.add_argument("--funciones", action="store_true", help="Mostrar funciones en el árbol.")
    p.add_argument("--clases", action="store_true", help="Mostrar clases en el árbol.")
    p.add_argument("--metodos", action="store_true", help="Mostrar métodos en el árbol (requiere --clases).")

    # --- Filters -------------------------------------------------------------
    p.add_argument(
        "--ext",
        dest="extensiones",
        default=None,
        help="Extensiones separadas por coma. Ej: .py,.txt",
    )
    p.add_argument(
        "--include",
        dest="patrones_incluir",
        default=None,
        help="Patrones regex de inclusión separados por coma (se aplican con re.match).",
    )
    p.add_argument(
        "--exclude",
        dest="patrones_excluir",
        default=None,
        help="Patrones regex de exclusión separados por coma (se aplican con re.match).",
    )

    # --- Safety / UX ---------------------------------------------------------
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Permitir sobrescritura si ya existen ficheros destino.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="No escribe ficheros; sólo valida y muestra qué ocurriría (si el pipeline lo soporta).",
    )
    p.add_argument(
        "--no-error-log",
        action="store_true",
        help="No generar el fichero de errores de transcripción.",
    )

    # --- Config handling -----------------------------------------------------
    p.add_argument(
        "--use-defaults",
        action="store_true",
        help="Ignora config.json y usa sólo valores por defecto + flags.",
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help="Imprime el config final (tras merges) en JSON y sale.",
    )

    # --- Output formatting ---------------------------------------------------
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Imprime el resultado final en JSON (útil para scripts).",
    )

    return p


# -----------------------------------------------------------------------------
# CLI: config normalization
# -----------------------------------------------------------------------------
def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    if value is None:
        return None
    parts = [x.strip() for x in value.split(",")]
    parts = [x for x in parts if x]
    return parts


def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge select keys where override is not None.
    Bool flags are merged explicitly (only if present in overrides).
    """
    out = dict(base)

    # Simple optional overrides
    for k in [
        "ruta_carpetas",
        "output_base_dir",
        "output_subdir_name",
        "output_prefix",
        "modo_procesamiento",
        "extensiones",
        "patrones_incluir",
        "patrones_excluir",
        "generar_arbol",
        "imprimir_arbol",
        "mostrar_funciones",
        "mostrar_clases",
        "mostrar_metodos",
        "guardar_log_errores",
    ]:
        if k in overrides and overrides[k] is not None:
            out[k] = overrides[k]

    return out


def _args_to_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    overrides: Dict[str, Any] = {}

    # Paths / naming
    overrides["ruta_carpetas"] = args.ruta_carpetas
    overrides["output_base_dir"] = args.output_base_dir
    overrides["output_subdir_name"] = args.output_subdir_name
    overrides["output_prefix"] = args.output_prefix

    # Mode
    if args.modo is not None:
        overrides["modo_procesamiento"] = args.modo

    # Filters
    ext = _split_csv(args.extensiones)
    inc = _split_csv(args.patrones_incluir)
    exc = _split_csv(args.patrones_excluir)
    if ext is not None:
        overrides["extensiones"] = ext
    if inc is not None:
        overrides["patrones_incluir"] = inc
    if exc is not None:
        overrides["patrones_excluir"] = exc

    # Tree flags
    if args.tree:
        overrides["generar_arbol"] = True
    if args.print_tree:
        overrides["imprimir_arbol"] = True
    if args.funciones:
        overrides["mostrar_funciones"] = True
    if args.clases:
        overrides["mostrar_clases"] = True
    if args.metodos:
        overrides["mostrar_metodos"] = True

    # Error log
    if args.no_error_log:
        overrides["guardar_log_errores"] = False

    return overrides


# -----------------------------------------------------------------------------
# CLI: output helpers
# -----------------------------------------------------------------------------
def _print_human_summary(result: Dict[str, Any]) -> None:
    ok = bool(result.get("ok"))
    if not ok:
        print("ERROR:", result.get("error", "Error desconocido"), file=sys.stderr)
        return

    salida = result.get("output_dir") or result.get("output_folder") or ""
    cont = result.get("contadores") or result.get("summary") or {}
    generados = result.get("generados") or result.get("outputs") or {}

    print("OK")
    if salida:
        print(f"Salida: {salida}")

    # Common counters
    if isinstance(cont, dict):
        for k in ["procesados", "omitidos", "errores", "tests_escritos", "modulos_escritos"]:
            if k in cont:
                print(f"{k}: {cont[k]}")

    # Common outputs
    if isinstance(generados, dict):
        for k in ["tests", "modulos", "errores", "arbol", "tree"]:
            v = generados.get(k)
            if v:
                print(f"{k}: {v}")


# -----------------------------------------------------------------------------
# CLI: main
# -----------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # -------------------------------------------------------------------------
    # Load base config
    # -------------------------------------------------------------------------
    if args.use_defaults:
        base_conf = cargar_configuracion_por_defecto()
    else:
        base_conf = cargar_configuracion()

    # -------------------------------------------------------------------------
    # Apply CLI overrides
    # -------------------------------------------------------------------------
    overrides = _args_to_overrides(args)
    conf = _merge_config(base_conf, overrides)

    conf["_cli_overwrite"] = bool(args.overwrite)
    conf["_cli_dry_run"] = bool(args.dry_run)
    if args.tree_file:
        conf["_cli_tree_file"] = args.tree_file

    # -------------------------------------------------------------------------
    # Optional: dump config and exit
    # -------------------------------------------------------------------------
    if args.dump_config:
        print(json.dumps(conf, ensure_ascii=False, indent=2))
        return 0

    # -------------------------------------------------------------------------
    # Basic validation
    # -------------------------------------------------------------------------
    ruta = (conf.get("ruta_carpetas") or "").strip()
    if ruta and not os.path.exists(ruta):
        print(f"ERROR: La ruta a procesar no existe: {ruta}", file=sys.stderr)
        return 2
    if ruta and not os.path.isdir(ruta):
        print(f"ERROR: La ruta a procesar no es un directorio: {ruta}", file=sys.stderr)
        return 2

    # -------------------------------------------------------------------------
    # Run pipeline
    # -------------------------------------------------------------------------
    try:
        result = run_pipeline(
            conf,
            overwrite=bool(args.overwrite),
            dry_run=bool(args.dry_run),
            tree_output_path=args.tree_file,
        )
    except KeyboardInterrupt:
        print("Interrumpido por el usuario.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"ERROR: Excepción no controlada: {e}", file=sys.stderr)
        return 1

    # -------------------------------------------------------------------------
    # Render output
    # -------------------------------------------------------------------------
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())