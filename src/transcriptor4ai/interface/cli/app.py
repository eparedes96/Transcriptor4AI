from __future__ import annotations

"""
Command Line Interface (CLI) Controller.

This module orchestrates the CLI workflow:
1. Initialize logging.
2. Load and merge configuration (Defaults + File + CLI Args).
3. Validate final configuration.
4. Execute the pipeline.
5. Render output (Human-readable or JSON).
"""

import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, Optional, List

from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.core.pipeline.validator import validate_config
from transcriptor4ai.domain.config import load_config, get_default_config
from transcriptor4ai.infra.logging import configure_logging, LoggingConfig, get_logger
from transcriptor4ai.interface.cli import args as cli_args
from transcriptor4ai.utils.i18n import i18n

logger = get_logger(__name__)


def main(argv: Optional[List[str]] = None) -> int:
    """
    CLI Main Entry Point.

    Args:
        argv: Optional list of command line arguments (defaults to sys.argv).

    Returns:
        int: Exit code (0 for success, non-zero for failure).
    """
    # 1. Parse Arguments
    parser = cli_args.build_parser()
    args = parser.parse_args(argv)

    # 2. Setup Logging (Console stderr only for CLI)
    log_level = "DEBUG" if args.debug else "INFO"
    logging_conf = LoggingConfig(level=log_level, console=True, log_file=None)
    configure_logging(logging_conf)

    logger.debug("CLI started. Parsing arguments...")

    # 3. Load Base Config
    if args.use_defaults:
        base_conf = get_default_config()
    else:
        base_conf = load_config()

    # 4. Apply Overrides
    overrides = cli_args.args_to_overrides(args)
    raw_conf = _merge_config(base_conf, overrides)

    # 5. Validate Configuration (Gatekeeper)
    clean_conf, warnings = validate_config(raw_conf, strict=False)

    if warnings:
        for w in warnings:
            logger.warning(f"Config Warning: {w}")

    # Special Flag: Dump Config
    if args.dump_config:
        print(json.dumps(clean_conf, ensure_ascii=False, indent=2))
        return 0

    # 6. Basic Path Check (Pre-Pipeline)
    input_path = clean_conf.get("input_path", "")
    if not os.path.exists(input_path):
        msg = i18n.t("cli.errors.path_not_exist", path=input_path)
        logger.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    # 7. Run Pipeline
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

    # 8. Render Output
    if args.json_output:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.ok else 1


def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge override values into the base config dictionary.
    Only merges known keys to prevent pollution.
    """
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


def _print_human_summary(result: PipelineResult) -> None:
    """
    Print a formatted, human-readable summary of the execution to stdout.
    This acts as the 'View' component for the CLI.
    """
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


if __name__ == "__main__":
    raise SystemExit(main())