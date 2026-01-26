from __future__ import annotations

"""
CLI Argument Definition and Mapping.

Defines the Command Line Interface schema, including grouping, help messages, 
and type specifications. Provides the translation logic to transform raw 
argparse Namespaces into domain-compatible configuration dictionaries.
"""

import argparse
from typing import Any, Dict

from transcriptor4ai.shared import converters as conv
from transcriptor4ai.shared.i18n import i18n

# ==============================================================================
# PARSER CONSTRUCTION
# ==============================================================================

def build_parser() -> argparse.ArgumentParser:
    """
    Construct and configure the ArgumentParser for the CLI.

    Organizes arguments into functional groups to improve documentation
    readability and CLI discoverability.

    Returns:
        argparse.ArgumentParser: The configured parser instance.
    """
    p = argparse.ArgumentParser(
        prog="transcriptor4ai",
        description=i18n.t("app.description"),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    # 1. GROUP: Path Management
    path_group = p.add_argument_group("Path Configuration")
    path_group.add_argument(
        "-i", "--input",
        dest="input_path",
        help=i18n.t("cli.args.input"),
    )
    path_group.add_argument(
        "-o", "--output-base",
        dest="output_base_dir",
        help=i18n.t("cli.args.output_base"),
    )
    path_group.add_argument(
        "--subdir",
        dest="output_subdir_name",
        help=i18n.t("cli.args.subdir"),
    )
    path_group.add_argument(
        "--prefix",
        dest="output_prefix",
        help=i18n.t("cli.args.prefix"),
    )

    # 2. GROUP: Content Scope and Analysis
    scope_group = p.add_argument_group("Content Discovery & Scope")
    scope_group.add_argument(
        "--no-modules",
        action="store_true",
        help=i18n.t("cli.args.no_modules"),
    )
    scope_group.add_argument(
        "--skeleton",
        action="store_true",
        help=i18n.t("cli.args.skeleton"),
    )
    scope_group.add_argument(
        "--no-tests",
        action="store_true",
        help=i18n.t("cli.args.no_tests"),
    )
    scope_group.add_argument(
        "--resources",
        action="store_true",
        help=i18n.t("cli.args.resources"),
    )
    scope_group.add_argument(
        "--tree",
        action="store_true",
        help=i18n.t("cli.args.tree"),
    )
    scope_group.add_argument(
        "--tree-file",
        dest="tree_file",
        help=i18n.t("cli.args.tree_file"),
    )

    # 3. GROUP: Static Analysis (AST)
    ast_group = p.add_argument_group("Static Analysis Features")
    ast_group.add_argument("--functions", action="store_true", help=i18n.t("cli.args.func"))
    ast_group.add_argument("--classes", action="store_true", help=i18n.t("cli.args.cls"))
    ast_group.add_argument("--methods", action="store_true", help=i18n.t("cli.args.meth"))
    ast_group.add_argument("--print-tree", action="store_true", help=i18n.t("cli.args.print_tree"))

    # 4. GROUP: Output Strategies
    output_group = p.add_argument_group("Output Control")
    output_group.add_argument(
        "--unified-only",
        action="store_true",
        help=i18n.t("cli.args.unified_only"),
    )
    output_group.add_argument(
        "--individual-only",
        action="store_true",
        help=i18n.t("cli.args.individual_only"),
    )

    # 5. GROUP: Filters and Security
    filter_group = p.add_argument_group("Filtering & Privacy")
    filter_group.add_argument(
        "--ext",
        dest="extensions",
        help=i18n.t("cli.args.ext"),
    )
    filter_group.add_argument(
        "--include",
        dest="include_patterns",
        help=i18n.t("cli.args.inc"),
    )
    filter_group.add_argument(
        "--exclude",
        dest="exclude_patterns",
        help=i18n.t("cli.args.exc"),
    )
    filter_group.add_argument(
        "--no-gitignore",
        action="store_true",
        help=i18n.t("cli.args.no_gitignore"),
    )

    # 6. GROUP: Operation & Diagnostics
    ops_group = p.add_argument_group("System & Debugging")
    ops_group.add_argument("--overwrite", action="store_true", help=i18n.t("cli.args.overwrite"))
    ops_group.add_argument("--dry-run", action="store_true", help=i18n.t("cli.args.dry_run"))
    ops_group.add_argument("--no-error-log", action="store_true", help=i18n.t("cli.args.no_log"))
    ops_group.add_argument("--use-defaults", action="store_true", help=i18n.t("cli.args.defaults"))
    ops_group.add_argument("--dump-config", action="store_true", help=i18n.t("cli.args.dump"))
    ops_group.add_argument("--debug", action="store_true", help="Elevate logging to DEBUG.")
    ops_group.add_argument("--json", dest="json_output", action="store_true", help=i18n.t("cli.args.json"))

    return p


# ==============================================================================
# NAMESPACE MAPPING
# ==============================================================================

def args_to_overrides(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Translate the argparse Namespace into a partial configuration dictionary.

    Args:
        args: The result of parser.parse_args().

    Returns:
        Dict[str, Any]: A flat dictionary containing only provided overrides.
    """
    overrides: Dict[str, Any] = {}

    # 1. MAP: Core path overrides
    overrides["input_path"] = args.input_path
    overrides["output_base_dir"] = args.output_base_dir
    overrides["output_subdir_name"] = args.output_subdir_name
    overrides["output_prefix"] = args.output_prefix

    # 2. MAP: Content scope and processing depth
    # Parsimonious logic: only set keys if flags are explicitly provided
    if args.skeleton:
        overrides["processing_depth"] = "skeleton"

    if args.no_modules:
        overrides["processing_depth"] = "tree_only"
        overrides["process_modules"] = False

    if args.no_tests:
        overrides["process_tests"] = False
    if args.resources:
        overrides["process_resources"] = True

    # 3. MAP: Output and Formatting
    if args.unified_only:
        overrides["create_individual_files"] = False
        overrides["create_unified_file"] = True
    elif args.individual_only:
        overrides["create_individual_files"] = True
        overrides["create_unified_file"] = False

    # 4. MAP: Collection-based filters
    # We delegate CSV parsing to shared converters for consistency
    if args.extensions:
        overrides["extensions"] = conv.to_list_str(args.extensions)
    if args.include_patterns:
        overrides["include_patterns"] = conv.to_list_str(args.include_patterns)
    if args.exclude_patterns:
        overrides["exclude_patterns"] = conv.to_list_str(args.exclude_patterns)

    # 5. MAP: Boolean flags and analysis options
    if args.no_gitignore:
        overrides["respect_gitignore"] = False
    if args.tree:
        overrides["generate_tree"] = True
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