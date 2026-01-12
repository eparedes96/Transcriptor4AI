from __future__ import annotations

"""
Unit tests for CLI Argument Parsing.

Verifies:
1. Mapping of CLI flags to configuration keys.
2. CSV string parsing logic.
3. Handling of boolean flags (store_true).
"""

from transcriptor4ai.interface.cli.args import build_parser, args_to_overrides


def parse_args(arg_list):
    """Helper to simulate CLI argument parsing."""
    parser = build_parser()
    return parser.parse_args(arg_list)


def test_cli_simple_flags_mapping():
    """Verify boolean flags are mapped correctly to config overrides."""
    args = parse_args([
        "--tree",
        "--print-tree",
        "--functions",
        "--no-error-log",
        "--no-modules",
        "--unified-only"
    ])

    overrides = args_to_overrides(args)

    assert overrides["generate_tree"] is True
    assert overrides["print_tree"] is True
    assert overrides["show_functions"] is True
    assert overrides["save_error_log"] is False
    assert overrides["process_modules"] is False

    # Shortcut logic
    assert overrides["create_individual_files"] is False
    assert overrides["create_unified_file"] is True


def test_cli_csv_list_parsing():
    """Verify comma-separated strings are parsed into lists."""
    args = parse_args([
        "--ext", ".js,.ts",
        "--exclude", "node_modules,dist"
    ])

    overrides = args_to_overrides(args)

    assert overrides["extensions"] == [".js", ".ts"]
    assert overrides["exclude_patterns"] == ["node_modules", "dist"]


def test_cli_path_arguments():
    """Verify input/output path arguments are captured."""
    args = parse_args([
        "-i", "/input/path",
        "-o", "/output/path",
        "--subdir", "my_sub",
        "--prefix", "my_prefix"
    ])

    overrides = args_to_overrides(args)

    assert overrides["input_path"] == "/input/path"
    assert overrides["output_base_dir"] == "/output/path"
    assert overrides["output_subdir_name"] == "my_sub"
    assert overrides["output_prefix"] == "my_prefix"


def test_cli_defaults_are_explicit_in_overrides():
    """
    Verify that argparse defaults are present in the override dict.
    Note: The merge logic in app.py handles None vs values.
    """
    args = parse_args([])
    overrides = args_to_overrides(args)

    assert overrides["input_path"] is None
    assert overrides["generate_tree"] is False