from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from transcriptor4ai.config import cargar_configuracion, cargar_configuracion_por_defecto
from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.pipeline import run_pipeline
from transcriptor4ai.logging import configure_logging, LoggingConfig, get_logger

# Initialize a logger for the CLI module itself
logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# CLI: Argument Parsing
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transcriptor4ai",
        description=(
            "Transcriptor4AI: Code transcription tool (Tests/Modules) with "
            "directory tree generation support."
        ),
    )

    # --- Input / Output ---
    p.add_argument(
        "-i", "--input",
        dest="ruta_carpetas",
        help="Path to the source directory to process.",
        default=None,
    )
    p.add_argument(
        "-o", "--output-base",
        dest="output_base_dir",
        help="Base output directory.",
        default=None,
    )
    p.add_argument(
        "--subdir",
        dest="output_subdir_name",
        help="Name of the output subdirectory.",
        default=None,
    )
    p.add_argument(
        "--prefix",
        dest="output_prefix",
        help="Prefix for generated files.",
        default=None,
    )

    # --- Mode / Features ---
    p.add_argument(
        "--modo",
        choices=["todo", "solo_modulos", "solo_tests"],
        default=None,
        help="Processing mode.",
    )
    p.add_argument(
        "--tree",
        action="store_true",
        help="Generate directory tree.",
    )
    p.add_argument(
        "--tree-file",
        dest="tree_file",
        default=None,
        help="Path to save the tree file (overrides default).",
    )
    p.add_argument(
        "--print-tree",
        action="store_true",
        help="Print the tree to console.",
    )

    # --- AST flags ---
    p.add_argument("--funciones", action="store_true", help="Show functions in tree.")
    p.add_argument("--clases", action="store_true", help="Show classes in tree.")
    p.add_argument("--metodos", action="store_true", help="Show methods in tree.")

    # --- Filters ---
    p.add_argument(
        "--ext",
        dest="extensiones",
        default=None,
        help="Comma-separated extensions (e.g. .py,.txt).",
    )
    p.add_argument(
        "--include",
        dest="patrones_incluir",
        default=None,
        help="Regex inclusion patterns.",
    )
    p.add_argument(
        "--exclude",
        dest="patrones_excluir",
        default=None,
        help="Regex exclusion patterns.",
    )

    # --- Safety / UX ---
    p.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing files without prompting.",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate execution without writing files.",
    )
    p.add_argument(
        "--no-error-log",
        action="store_true",
        help="Do not generate the error log file.",
    )

    # --- Config handling ---
    p.add_argument(
        "--use-defaults",
        action="store_true",
        help="Ignore config.json and use defaults.",
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help="Print final config in JSON and exit.",
    )
    p.add_argument(
        "--debug",
        action="store_true",
        help="Enable DEBUG logging level.",
    )

    # --- Output formatting ---
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Output result in JSON format.",
    )

    return p


# -----------------------------------------------------------------------------
# CLI: Helpers
# -----------------------------------------------------------------------------
def _split_csv(value: Optional[str]) -> Optional[list[str]]:
    if value is None:
        return None
    parts = [x.strip() for x in value.split(",")]
    parts = [x for x in parts if x]
    return parts


def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge overrides into base config."""
    out = dict(base)
    keys_to_merge = [
        "ruta_carpetas", "output_base_dir", "output_subdir_name", "output_prefix",
        "modo_procesamiento", "extensiones", "patrones_incluir", "patrones_excluir",
        "generar_arbol", "imprimir_arbol", "mostrar_funciones", "mostrar_clases",
        "mostrar_metodos", "guardar_log_errores",
    ]
    for k in keys_to_merge:
        if k in overrides and overrides[k] is not None:
            out[k] = overrides[k]
    return out


def _args_to_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """Map argparse Namespace to config dictionary keys."""
    overrides: Dict[str, Any] = {}

    overrides["ruta_carpetas"] = args.ruta_carpetas
    overrides["output_base_dir"] = args.output_base_dir
    overrides["output_subdir_name"] = args.output_subdir_name
    overrides["output_prefix"] = args.output_prefix

    if args.modo is not None:
        overrides["modo_procesamiento"] = args.modo

    if args.extensiones:
        overrides["extensiones"] = _split_csv(args.extensiones)
    if args.patrones_incluir:
        overrides["patrones_incluir"] = _split_csv(args.patrones_incluir)
    if args.patrones_excluir:
        overrides["patrones_excluir"] = _split_csv(args.patrones_excluir)

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
    if args.no_error_log:
        overrides["guardar_log_errores"] = False

    return overrides


def _print_human_summary(result: Dict[str, Any]) -> None:
    ok = bool(result.get("ok"))
    if not ok:
        print("ERROR:", result.get("error", "Unknown error"), file=sys.stderr)
        return

    salida = result.get("output_dir") or result.get("salida_real") or ""
    cont = result.get("contadores") or result.get("summary") or {}
    generados = result.get("generados") or {}
    resumen_data = result.get("resumen") or {}

    print("SUCCESS")
    if salida:
        print(f"Output Directory: {salida}")

    # Merge counters from various possible result structures
    counters = cont if cont else resumen_data
    for k in ["procesados", "omitidos", "errores", "tests_escritos", "modulos_escritos"]:
        if k in counters:
            print(f"{k}: {counters[k]}")

    if generados:
        print("\nGenerated Files:")
        for k, v in generados.items():
            if v:
                print(f"  - {k}: {v}")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # 1. Setup Logging (Console stderr only for CLI)
    log_level = "DEBUG" if args.debug else "INFO"
    logging_conf = LoggingConfig(level=log_level, console=True, log_file=None)
    configure_logging(logging_conf)

    logger.debug("CLI started. Parsing arguments...")

    # 2. Load Base Config
    if args.use_defaults:
        base_conf = cargar_configuracion_por_defecto()
    else:
        base_conf = cargar_configuracion()

    # 3. Apply Overrides
    overrides = _args_to_overrides(args)
    raw_conf = _merge_config(base_conf, overrides)

    # 4. Validate Configuration (Gatekeeper)
    clean_conf, warnings = validate_config(raw_conf, strict=False)

    if warnings:
        for w in warnings:
            logger.warning(f"Config Warning: {w}")

    # Add CLI-specific runtime flags not in config schema
    clean_conf["_cli_overwrite"] = bool(args.overwrite)
    clean_conf["_cli_dry_run"] = bool(args.dry_run)
    if args.tree_file:
        clean_conf["_cli_tree_file"] = args.tree_file

    if args.dump_config:
        print(json.dumps(clean_conf, ensure_ascii=False, indent=2))
        return 0

    # 5. Basic Path Check (Pre-Pipeline)
    ruta = clean_conf.get("ruta_carpetas", "")
    if not os.path.exists(ruta):
        logger.error(f"Input path does not exist: {ruta}")
        return 2

    # 6. Run Pipeline
    logger.info(f"Starting pipeline for input: {ruta}")
    try:
        result = run_pipeline(
            clean_conf,
            overwrite=bool(args.overwrite),
            dry_run=bool(args.dry_run),
        )
    except KeyboardInterrupt:
        logger.warning("Operation cancelled by user (SIGINT).")
        return 130
    except Exception as e:
        logger.critical(f"Unhandled exception in pipeline: {e}", exc_info=True)
        return 1

    # 7. Render Output
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())