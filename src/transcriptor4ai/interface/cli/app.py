from __future__ import annotations

"""
Command Line Interface (CLI) Application Controller.

Orchestrates the CLI lifecycle: initialization of logging, loading and merging 
of configuration sources (defaults, persistent storage, and CLI overrides), 
pipeline execution, and result rendering. Acts as the primary interface for 
automation and headless environments.
"""

import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from transcriptor4ai.core.pipeline.engine import run_pipeline
from transcriptor4ai.core.pipeline.stages.validator import validate_config
from transcriptor4ai.domain.config import get_default_config, load_config
from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.infra.logging import LoggingConfig, configure_logging, get_logger
from transcriptor4ai.interface.cli import args as cli_args
from transcriptor4ai.utils.i18n import i18n

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# ENTRYPOINT ORCHESTRATOR
# -----------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    """
    Execute the main CLI application workflow.

    Args:
        argv: Optional list of command line arguments. Defaults to sys.argv.

    Returns:
        int: Process exit code (0 for success, non-zero for failure).
    """
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    # 1. Argument parsing phase
    parser = cli_args.build_parser()
    args = parser.parse_args(argv)

    # 2. Logging bootstrap (CLI-specific: Console stderr)
    log_level = "DEBUG" if args.debug else "INFO"
    logging_conf = LoggingConfig(level=log_level, console=True, log_file=None)
    configure_logging(logging_conf)

    logger.debug("CLI execution initiated. Resolving configuration hierarchy...")

    # 3. Resolve base configuration (Default vs Persistent state)
    if args.use_defaults:
        base_conf = get_default_config()
    else:
        base_conf = load_config()

    # 4. Map and merge command-line overrides
    overrides = cli_args.args_to_overrides(args)
    raw_conf = _merge_config(base_conf, overrides)

    # 5. Schema validation and normalization
    clean_conf, warnings = validate_config(raw_conf, strict=False)

    if warnings:
        for w in warnings:
            logger.warning(f"Configuration Constraint: {w}")

    # Short-circuit if configuration dump is requested
    if args.dump_config:
        print(json.dumps(clean_conf, ensure_ascii=False, indent=2))
        return 0

    # 6. Pre-flight input verification
    input_path = clean_conf.get("input_path", "")
    if not os.path.exists(input_path):
        msg = i18n.t("cli.errors.path_not_exist", path=input_path)
        logger.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    # 7. Pipeline execution phase
    logger.info(f"Targeting input directory: {input_path}")
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

    # 8. Output rendering phase
    if args.json_output:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.ok else 1

# -----------------------------------------------------------------------------
# CONFIGURATION MERGING
# -----------------------------------------------------------------------------

def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """
    Perform a shallow merge of override values into the base configuration.

    Filters input to ensure only known keys are merged, preventing schema
    pollution from external sources.

    Args:
        base: The primary configuration dictionary.
        overrides: New values to inject.

    Returns:
        Dict[str, Any]: The merged configuration state.
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

# -----------------------------------------------------------------------------
# VIEW RENDERING (HUMAN READABLE)
# -----------------------------------------------------------------------------

def _print_human_summary(result: PipelineResult) -> None:
    """
    Format and print the execution result to the standard output.

    Acts as the 'View' component for the CLI interface, transforming
    the PipelineResult domain model into a structured terminal report.

    Args:
        result: The pipeline result to render.
    """
    if not result.ok:
        print(f"ERROR: {result.error}", file=sys.stderr)
        return

    summary = result.summary
    dry_run = summary.get("dry_run", False)

    print(i18n.t("cli.status.success"))

    # Simulation-specific report
    if dry_run:
        print(i18n.t("gui.popups.dry_run_title"))
        print(f"Target path: {result.final_output_path}")
        print(f"Projected generation: {summary.get('will_generate')}")
        return

    # Physical execution report
    if result.final_output_path:
        print(i18n.t("cli.status.output_dir", path=result.final_output_path))

    # Metric visualization
    if result.token_count > 0:
        print(f"Estimated Token Density: {result.token_count:,}")

    # Execution statistics
    stats_keys = {
        "processed": "Files processed",
        "skipped": "Files skipped",
        "errors": "Critical errors"
    }
    for key, label in stats_keys.items():
        if key in summary:
            print(f"{label}: {summary[key]}")

    # Artifact list
    gen_files = summary.get("generated_files", {})
    if gen_files:
        print("\n" + i18n.t("cli.status.generated"))
        for k, v in gen_files.items():
            if v:
                print(f"  - {k}: {v}")

    # Static analysis metadata
    tree_info = summary.get("tree", {})
    if tree_info.get("generated"):
        tree_path = tree_info.get('path')
        if not tree_path and 'unified' in gen_files:
            tree_path = "(Aggregated into Unified File)"

        lines = tree_info.get('lines', 0)
        print(f"  - structure tree: {tree_path} ({lines} lines)")

# -----------------------------------------------------------------------------
# CLI ENTRYPOINT
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit(main())