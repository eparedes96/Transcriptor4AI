from __future__ import annotations

"""
CLI Argument Definition and Mapping.

Defines the command-line interface schema, including help messages, 
argument types, and defaults. Provides logic to translate raw argparse 
namespaces into domain-compatible configuration overrides.
"""

import argparse
from typing import Any, Dict, List, Optional

from transcriptor4ai.utils.i18n import i18n

# -----------------------------------------------------------------------------
# ARGUMENT DEFINITION
# -----------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """
    Construct the argument parser for the Transcriptor4AI CLI.

    Returns:
        argparse.ArgumentParser: Configured parser instance.
    """
    p = argparse.ArgumentParser(
        prog="transcriptor4ai",
        description=i18n.t("app.description"),
    )

    # --- Path Management ---
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

    # --- Content Discovery and Selection ---
    p.add_argument(
        "--no-modules",
        action="store_true",
        help=i18n.t("cli.args.no_modules", default="Exclude source code logic."),
    )
    p.add_argument(
        "--no-tests",
        action="store_true",
        help=i18n.t("cli.args.no_tests", default="Exclude test suite files."),
    )
    p.add_argument(
        "--resources",
        action="store_true",
        help=i18n.t("cli.args.resources", default="Include non-code resources (docs/config)."),
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

    # --- Output Strategies ---
    p.add_argument(
        "--unified-only",
        action="store_true",
        help=i18n.t("cli.args.unified_only", default="Target ONLY unified context generation."),
    )
    p.add_argument(
        "--individual-only",
        action="store_true",
        help=i18n.t("cli.args.individual_only", default="Target ONLY categorized file generation."),
    )

    # --- Static Analysis (AST) Configuration ---
    p.add_argument("--functions", action="store_true", help=i18n.t("cli.args.func"))
    p.add_argument("--classes", action="store_true", help=i18n.t("cli.args.cls"))
    p.add_argument("--methods", action="store_true", help=i18n.t("cli.args.meth"))

    # --- Data Transformation Filters ---
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
        help=i18n.t("cli.args.no_gitignore", default="Ignore local .gitignore rules."),
    )

    # --- Runtime Constraints and Safety ---
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

    # --- Configuration and Diagnostic Tools ---
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
        help="Elevate logging verbosity to DEBUG.",
    )

    # --- Format Selection ---
    p.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help=i18n.t("cli.args.json"),
    )

    return p

# -----------------------------------------------------------------------------
# ARGUMENT MAPPING
# -----------------------------------------------------------------------------

def args_to_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Translate the argparse Namespace into a domain configuration dictionary.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Dict[str, Any]: Configuration overrides subset.
    """
    overrides: Dict[str, Any] = {}

    overrides["input_path"] = args.input_path
    overrides["output_base_dir"] = args.output_base_dir
    overrides["output_subdir_name"] = args.output_subdir_name
    overrides["output_prefix"] = args.output_prefix

    # Content Scope overrides
    if args.no_modules:
        overrides["process_modules"] = False
    if args.no_tests:
        overrides["process_tests"] = False
    if args.resources:
        overrides["process_resources"] = True

    # Analysis overrides
    if args.tree:
        overrides["generate_tree"] = True

    # Output Format overrides
    if args.unified_only:
        overrides["create_individual_files"] = False
        overrides["create_unified_file"] = True
    elif args.individual_only:
        overrides["create_individual_files"] = True
        overrides["create_unified_file"] = False

    # Logic-based filtering overrides
    if args.extensions:
        overrides["extensions"] = _split_csv(args.extensions)
    if args.include_patterns:
        overrides["include_patterns"] = _split_csv(args.include_patterns)
    if args.exclude_patterns:
        overrides["exclude_patterns"] = _split_csv(args.exclude_patterns)
    if args.no_gitignore:
        overrides["respect_gitignore"] = False

    # Detailed Analysis flags
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

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------

def _split_csv(value: Optional[str]) -> Optional[List[str]]:
    """
    Convert a comma-separated string into a list of sanitized strings.
    """
    if value is None:
        return None
    parts = [x.strip() for x in value.split(",")]
    return [x for x in parts if x]