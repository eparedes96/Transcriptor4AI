from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict, Optional

from transcriptor4ai.config import load_config, get_default_config
from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.pipeline import run_pipeline
from transcriptor4ai.logging import configure_logging, LoggingConfig, get_logger
from transcriptor4ai.utils.i18n import i18n

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# CLI: Argument Parsing
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transcriptor4ai",
        description=i18n.t("app.description"),
    )

    # --- Input / Output ---
    p.add_argument(
        "-i", "--input",
        dest="input_path",
        help=i18n.t("cli.args.input"),
        default=None,
    )
    p.add_argument(
        "-o", "--output-base",
        dest="output_base_dir",
        help=i18n.t("cli.args.output_base"),
        default=None,
    )
    p.add_argument(
        "--subdir",
        dest="output_subdir_name",
        help=i18n.t("cli.args.subdir"),
        default=None,
    )
    p.add_argument(
        "--prefix",
        dest="output_prefix",
        help=i18n.t("cli.args.prefix"),
        default=None,
    )

    # --- Mode / Features ---
    p.add_argument(
        "--modo",
        choices=["todo", "solo_modulos", "solo_tests"],
        default=None,
        help=i18n.t("cli.args.mode"),
    )
    p.add_argument(
        "--tree",
        action="store_true",
        help=i18n.t("cli.args.tree"),
    )
    p.add_argument(
        "--tree-file",
        dest="tree_file",
        default=None,
        help=i18n.t("cli.args.tree_file"),
    )
    p.add_argument(
        "--print-tree",
        action="store_true",
        help=i18n.t("cli.args.print_tree"),
    )

    # --- AST flags ---
    p.add_argument("--funciones", action="store_true", help=i18n.t("cli.args.func"))
    p.add_argument("--clases", action="store_true", help=i18n.t("cli.args.cls"))
    p.add_argument("--metodos", action="store_true", help=i18n.t("cli.args.meth"))

    # --- Filters ---
    p.add_argument(
        "--ext",
        dest="extensiones",
        default=None,
        help=i18n.t("cli.args.ext"),
    )
    p.add_argument(
        "--include",
        dest="include_patterns",
        default=None,
        help=i18n.t("cli.args.inc"),
    )
    p.add_argument(
        "--exclude",
        dest="exclude_patterns",
        default=None,
        help=i18n.t("cli.args.exc"),
    )

    # --- Safety / UX ---
    p.add_argument(
        "--overwrite",
        action="store_true",
        help=i18n.t("cli.args.overwrite"),
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help=i18n.t("cli.args.dry_run"),
    )
    p.add_argument(
        "--no-error-log",
        action="store_true",
        help=i18n.t("cli.args.no_log"),
    )

    # --- Config handling ---
    p.add_argument(
        "--use-defaults",
        action="store_true",
        help=i18n.t("cli.args.defaults"),
    )
    p.add_argument(
        "--dump-config",
        action="store_true",
        help=i18n.t("cli.args.dump"),
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
        help=i18n.t("cli.args.json"),
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
        "input_path", "output_base_dir", "output_subdir_name", "output_prefix",
        "processing_mode", "extensiones", "include_patterns", "exclude_patterns",
        "generate_tree", "print_tree", "show_functions", "show_classes",
        "show_methods", "save_error_log",
    ]
    for k in keys_to_merge:
        if k in overrides and overrides[k] is not None:
            out[k] = overrides[k]
    return out


def _args_to_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """Map argparse Namespace to config dictionary keys."""
    overrides: Dict[str, Any] = {}

    overrides["input_path"] = args.input_path
    overrides["output_base_dir"] = args.output_base_dir
    overrides["output_subdir_name"] = args.output_subdir_name
    overrides["output_prefix"] = args.output_prefix

    if args.modo is not None:
        overrides["processing_mode"] = args.modo

    if args.extensiones:
        overrides["extensiones"] = _split_csv(args.extensiones)
    if args.include_patterns:
        overrides["include_patterns"] = _split_csv(args.include_patterns)
    if args.exclude_patterns:
        overrides["exclude_patterns"] = _split_csv(args.exclude_patterns)

    if args.tree:
        overrides["generate_tree"] = True
    if args.print_tree:
        overrides["print_tree"] = True
    if args.funciones:
        overrides["show_functions"] = True
    if args.clases:
        overrides["show_classes"] = True
    if args.metodos:
        overrides["show_methods"] = True
    if args.no_error_log:
        overrides["save_error_log"] = False

    return overrides


def _print_human_summary(result: Dict[str, Any]) -> None:
    ok = bool(result.get("ok"))
    if not ok:
        print(f"ERROR: {result.get('error', 'Unknown error')}", file=sys.stderr)
        return

    salida = result.get("output_dir") or result.get("salida_real") or ""
    cont = result.get("contadores") or result.get("summary") or {}
    generados = result.get("generados") or {}
    resumen_data = result.get("resumen") or {}

    print(i18n.t("cli.status.success"))
    if salida:
        print(i18n.t("cli.status.output_dir", path=salida))

    # Merge counters from various possible result structures
    counters = cont if cont else resumen_data
    for k in ["procesados", "omitidos", "errores", "tests_escritos", "modulos_escritos"]:
        if k in counters:
            print(f"{k}: {counters[k]}")

    if generados:
        print("\n" + i18n.t("cli.status.generated"))
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
        base_conf = get_default_config()
    else:
        base_conf = load_config()

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
    ruta = clean_conf.get("input_path", "")
    if not os.path.exists(ruta):
        msg = i18n.t("cli.errors.path_not_exist", path=ruta)
        logger.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
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
        msg = i18n.t("cli.status.interrupted")
        logger.warning(msg)
        print(msg, file=sys.stderr)
        return 130
    except Exception as e:
        msg = i18n.t("cli.errors.pipeline_fail", error=e)
        logger.critical(msg, exc_info=True)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    # 7. Render Output
    if args.json_output:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())