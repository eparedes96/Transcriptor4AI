from __future__ import annotations

"""
Command Line Interface (CLI) for transcriptor4ai.

Handles argument parsing, configuration merging, and terminal-based 
execution of the transcription pipeline. Synchronized with the English 
core API and PipelineResult dataclass.
"""

import argparse
import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, Optional

from transcriptor4ai.domain.config import load_config, get_default_config
from transcriptor4ai.core.pipeline.validator import validate_config
from transcriptor4ai.core.pipeline.engine import run_pipeline, PipelineResult
from transcriptor4ai.infra.logging import configure_logging, LoggingConfig, get_logger
from transcriptor4ai.utils.i18n import i18n

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
# CLI: Argument Parsing
# -----------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the CLI."""
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

    # --- Content Selection ---
    p.add_argument(
        "--no-modules",
        action="store_true",
        help=i18n.t("cli.args.no_modules", default="Do not include source code modules."),
    )
    p.add_argument(
        "--no-tests",
        action="store_true",
        help=i18n.t("cli.args.no_tests", default="Do not include test files."),
    )
    p.add_argument(
        "--resources",
        action="store_true",
        help=i18n.t("cli.args.resources", default="Include resource files (docs, config, data)."),
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

    # --- Output Format Shortcuts ---
    p.add_argument(
        "--unified-only",
        action="store_true",
        help=i18n.t("cli.args.unified_only", default="Generate ONLY the unified context file."),
    )
    p.add_argument(
        "--individual-only",
        action="store_true",
        help=i18n.t("cli.args.individual_only", default="Generate ONLY individual files."),
    )

    # --- AST flags ---
    p.add_argument("--functions", action="store_true", help=i18n.t("cli.args.func"))
    p.add_argument("--classes", action="store_true", help=i18n.t("cli.args.cls"))
    p.add_argument("--methods", action="store_true", help=i18n.t("cli.args.meth"))

    # --- Filters ---
    p.add_argument(
        "--ext",
        dest="extensions",
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
    p.add_argument(
        "--no-gitignore",
        action="store_true",
        help=i18n.t("cli.args.no_gitignore", default="Do not read .gitignore files."),
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
    """Split a comma-separated string into a list of strings."""
    if value is None:
        return None
    parts = [x.strip() for x in value.split(",")]
    return [x for x in parts if x]


def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Merge overrides into base config dictionary."""
    out = dict(base)
    keys_to_merge = [
        "input_path", "output_base_dir", "output_subdir_name", "output_prefix",
        "process_modules", "process_tests", "process_resources",
        "create_individual_files", "create_unified_file",
        "extensions", "include_patterns", "exclude_patterns",
        "generate_tree", "print_tree", "show_functions", "show_classes",
        "show_methods", "save_error_log", "respect_gitignore"
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

    # Content Selection Mapping
    if args.no_modules:
        overrides["process_modules"] = False
    if args.no_tests:
        overrides["process_tests"] = False
    if args.resources:
        overrides["process_resources"] = True

    # Tree mapping
    if args.tree:
        overrides["generate_tree"] = True

    # Output Format Mapping (Shortcuts)
    if args.unified_only:
        overrides["create_individual_files"] = False
        overrides["create_unified_file"] = True
    elif args.individual_only:
        overrides["create_individual_files"] = True
        overrides["create_unified_file"] = False

    # Filters
    if args.extensions:
        overrides["extensions"] = _split_csv(args.extensions)
    if args.include_patterns:
        overrides["include_patterns"] = _split_csv(args.include_patterns)
    if args.exclude_patterns:
        overrides["exclude_patterns"] = _split_csv(args.exclude_patterns)
    if args.no_gitignore:
        overrides["respect_gitignore"] = False

    # AST Options
    if args.print_tree:
        overrides["print_tree"] = True
    if args.functions:
        overrides["show_functions"] = True
    if args.classes:
        overrides["show_classes"] = True
    if args.methods:
        overrides["show_methods"] = True
    if args.no_error_log:
        overrides["save_error_log"] = False

    return overrides


def _print_human_summary(result: PipelineResult) -> None:
    """Print a human-readable summary of the pipeline execution to stdout/stderr."""
    if not result.ok:
        print(f"ERROR: {result.error}", file=sys.stderr)
        return

    summary = result.summary
    dry_run = summary.get("dry_run", False)

    print(i18n.t("cli.status.success"))

    if dry_run:
        print(i18n.t("gui.popups.dry_run_title"))
        print(f"Target path: {result.final_output_path}")
        print(f"Files to generate: {summary.get('will_generate')}")
        return

    if result.final_output_path:
        print(i18n.t("cli.status.output_dir", path=result.final_output_path))

    # Token Count
    if result.token_count > 0:
        print(f"Estimated Tokens: {result.token_count:,}")

    # Print Statistics using English keys
    stats_keys = {
        "processed": "Processed files",
        "skipped": "Skipped files",
        "errors": "Errors encountered"
    }
    for key, label in stats_keys.items():
        if key in summary:
            print(f"{label}: {summary[key]}")

    # Print Generated Files details
    gen_files = summary.get("generated_files", {})
    if gen_files:
        print("\n" + i18n.t("cli.status.generated"))
        for k, v in gen_files.items():
            if v:
                print(f"  - {k}: {v}")

    # Tree info
    tree_info = summary.get("tree", {})
    if tree_info.get("generated"):
        tree_path = tree_info.get('path')
        if not tree_path and 'unified' in gen_files:
            tree_path = "(Inside Unified File)"

        lines = tree_info.get('lines', 0)
        print(f"  - tree: {tree_path} ({lines} lines)")


# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------
def main(argv: Optional[list[str]] = None) -> int:
    """CLI Main Entry Point."""
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

    if args.dump_config:
        print(json.dumps(clean_conf, ensure_ascii=False, indent=2))
        return 0

    # 5. Basic Path Check (Pre-Pipeline)
    input_path = clean_conf.get("input_path", "")
    if not os.path.exists(input_path):
        msg = i18n.t("cli.errors.path_not_exist", path=input_path)
        logger.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    # 6. Run Pipeline
    logger.info(f"Starting pipeline for input: {input_path}")
    try:
        result = run_pipeline(
            clean_conf,
            overwrite=bool(args.overwrite),
            dry_run=bool(args.dry_run),
            tree_output_path=args.tree_file
        )
    except KeyboardInterrupt:
        msg = i18n.t("cli.status.interrupted")
        logger.warning(msg)
        print(msg, file=sys.stderr)
        return 130
    except Exception as e:
        msg = i18n.t("cli.errors.pipeline_fail", error=str(e))
        logger.critical(msg, exc_info=True)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    # 7. Render Output
    if args.json_output:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())