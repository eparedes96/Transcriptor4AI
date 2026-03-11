from __future__ import annotations

"""
Command Line Interface (CLI) Application Controller.

Orchestrates the CLI lifecycle by:
1. Bootstrapping diagnostic infrastructure (Logging).
2. Instantiating concrete infrastructure adapters (Filesystem, Cache, Config).
3. Merging configuration hierarchy (Defaults -> Persistent -> CLI Overrides).
4. Executing the decoupled pipeline via Dependency Injection.
5. Rendering results in human-readable or machine-parsable (JSON) formats.
"""

import json
import os
import sys
from dataclasses import asdict
from typing import Any, Dict, List, Optional

# Application Pipeline
from transcriptor4ai.application.pipeline.orchestrator import run_pipeline
from transcriptor4ai.application.pipeline.stages.validator import validate_config

# Domain Entities & Results
from transcriptor4ai.domain.entities.app_config import get_default_config
from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.infrastructure import UserContextAdapter

# Infrastructure Implementation (Concrete Adapters)
from transcriptor4ai.infrastructure.logging import LoggingConfig, configure_logging, get_logger
from transcriptor4ai.infrastructure.persistence.json_config_repo import JsonConfigRepository
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

# Interface Utilities
from transcriptor4ai.interface.cli import argument_parser as cli_args
from transcriptor4ai.shared.i18n import i18n

# Standard logger initialization
logger = get_logger(__name__)


# ==============================================================================
# CLI ENTRYPOINT ORCHESTRATOR
# ==============================================================================

def main(argv: Optional[List[str]] = None) -> int:
    """
    Execute the main CLI application workflow.

    Args:
        argv: Optional list of command line arguments. Defaults to sys.argv.

    Returns:
        int: Process exit code (0: Success, 1: Error, 2: IO/Config Error).
    """
    # 1. BOOTSTRAP: Ensure UTF-8 compatibility for Windows consoles
    if sys.platform == "win32":
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")

    # 2. PARSE: Extract arguments from command line
    parser = cli_args.build_parser()
    args = parser.parse_args(argv)

    # 3. LOGGING: Initialize system diagnostics based on debug flag
    log_level = "DEBUG" if args.debug else "INFO"
    logging_conf = LoggingConfig(level=log_level, console=True, log_file=None)
    configure_logging(logging_conf)

    logger.debug("CLI: Execution sequence started. Bootstrapping infrastructure...")

    # 4. INFRASTRUCTURE: Instantiate concrete implementation adapters
    fs = FileSystemAdapter()
    cache = SqliteCacheRepository(fs)
    user_context = UserContextAdapter()
    config_repo = JsonConfigRepository(fs)

    # 5. CONFIGURATION: Resolve final state through merging layers
    current_cwd = os.getcwd()

    # Layer A: Base (Defaults vs Persistent state)
    if args.use_defaults:
        base_conf = get_default_config(current_cwd)
    else:
        base_conf = config_repo.load_config()

    # Layer B: Overrides (Command-line arguments)
    overrides = cli_args.args_to_overrides(args)
    raw_conf = _merge_config(base_conf, overrides)

    # Layer C: Validation (Schema enforcement and normalization)
    clean_conf, warnings = validate_config(raw_conf, base_path=current_cwd, strict=False)

    for w in warnings:
        logger.warning(f"CLI: Configuration constraint -> {w}")

    # Tooling: Support configuration inspection without execution
    if args.dump_config:
        print(json.dumps(clean_conf, ensure_ascii=False, indent=2))
        return 0

    # 6. PRE-FLIGHT: Verify primary input directory via infrastructure adapter
    input_path = clean_conf.get("input_path", "")
    if not fs.file_exists(input_path) and not os.path.isdir(input_path):
        msg = i18n.t("cli.errors.path_not_exist", path=input_path)
        logger.error(msg)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 2

    # 7. EXECUTION: Launch the decoupled pipeline using DI
    logger.info(f"CLI: Targeting source directory -> {input_path}")
    try:
        result = run_pipeline(
            fs=fs,
            cache=cache,
            user_context=user_context,
            config=clean_conf,
            overwrite=bool(args.overwrite),
            dry_run=bool(args.dry_run),
            tree_output_path=args.tree_file
        )
    except KeyboardInterrupt:
        msg = i18n.t("cli.status.interrupted")
        logger.warning(msg)
        print(f"\n{msg}", file=sys.stderr)
        return 130
    except Exception as e:
        msg = i18n.t("cli.errors.pipeline_fail", error=str(e))
        logger.critical(msg, exc_info=True)
        print(f"ERROR: {msg}", file=sys.stderr)
        return 1

    # 8. PRESENTATION: Render results to the user
    if args.json_output:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    else:
        _print_human_summary(result)

    return 0 if result.ok else 1


# ==============================================================================
# PRIVATE HELPERS: LOGIC & VIEW
# ==============================================================================

def _merge_config(base: Dict[str, Any], overrides: Dict[str, Any]) -> Dict[str, Any]:
    """Perform a shallow merge of CLI overrides into base configuration."""
    out = dict(base)
    # Define keys that are explicitly allowed to be overridden by terminal flags
    keys_to_merge = [
        "input_path", "output_base_dir", "output_subdir_name", "output_prefix",
        "process_modules", "process_tests", "process_resources",
        "create_individual_files", "create_unified_file",
        "extensions", "include_patterns", "exclude_patterns",
        "generate_tree", "print_tree", "show_functions", "show_classes",
        "show_methods", "save_error_log", "respect_gitignore", "processing_depth"
    ]
    for k in keys_to_merge:
        if k in overrides and overrides[k] is not None:
            out[k] = overrides[k]
    return out


def _print_human_summary(result: PipelineResult) -> None:
    """Format and print the execution result to the standard output."""
    if not result.ok:
        print(f"ERROR: {result.error}", file=sys.stderr)
        return

    summary = result.summary
    dry_run = summary.get("dry_run", False)

    print(f"\n{i18n.t('cli.status.success')}")

    # Report: Simulation State
    if dry_run:
        print(f"--- {i18n.t('gui.popups.dry_run_title')} ---")
        print(f"Projected output path: {result.final_output_path}")
        return

    # Report: Production Metrics
    if result.final_output_path:
        print(f"{i18n.t('cli.status.output_dir', path=result.final_output_path)}")

    if result.token_count > 0:
        print(f"Calculated Token Density: {result.token_count:,}")

    # Stats Section
    stats = {
        "processed": "Files Processed",
        "skipped": "Files Skipped",
        "errors": "Critical Failures"
    }
    for key, label in stats.items():
        if key in summary:
            print(f"  - {label}: {summary[key]}")

    # Artifact Discovery
    gen_files = summary.get("generated_files", {})
    if gen_files:
        print(f"\n{i18n.t('cli.status.generated')}")
        for k, v in gen_files.items():
            if v:
                print(f"    * [{k.upper()}]: {v}")

    # Static Analysis Summary
    tree_info = summary.get("tree", {})
    if tree_info.get("generated"):
        lines = tree_info.get('lines', 0)
        print(f"    * [TREE]: {lines} structural lines mapped.")


# ==============================================================================
# ENTRYPOINT SCRIPT
# ==============================================================================

if __name__ == "__main__":
    sys.exit(main())