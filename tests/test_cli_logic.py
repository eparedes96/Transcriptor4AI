from __future__ import annotations

"""
Unit tests for CLI argument parsing and mapping logic.
"""

from transcriptor4ai.interface.cli.args import _build_parser, _args_to_overrides


def parse_args(arg_list):
    """Helper to simulate CLI argument parsing."""
    parser = _build_parser()
    return parser.parse_args(arg_list)


# -----------------------------------------------------------------------------
# CLI Argument Mapping Tests
# -----------------------------------------------------------------------------

def test_cli_simple_flags_mapping():
    """Verify boolean flags are mapped correctly."""
    args = parse_args([
        "--tree",
        "--print-tree",
        "--functions",
        "--no-error-log",
        "--no-modules",
        "--unified-only"
    ])

    overrides = _args_to_overrides(args)

    assert overrides["generate_tree"] is True
    assert overrides["print_tree"] is True
    assert overrides["show_functions"] is True
    assert overrides["save_error_log"] is False
    assert overrides["process_modules"] is False
    assert overrides["create_individual_files"] is False
    assert overrides["create_unified_file"] is True


def test_cli_csv_list_parsing():
    """Verify comma-separated strings are parsed into lists."""
    args = parse_args([
        "--ext", ".js,.ts",
        "--exclude", "node_modules,dist"
    ])

    overrides = _args_to_overrides(args)

    assert overrides["extensions"] == [".js", ".ts"]
    assert overrides["exclude_patterns"] == ["node_modules", "dist"]


def test_cli_path_arguments():
    """Verify input/output path arguments."""
    args = parse_args([
        "-i", "/input/path",
        "-o", "/output/path",
        "--subdir", "my_sub",
        "--prefix", "my_prefix"
    ])

    overrides = _args_to_overrides(args)

    assert overrides["input_path"] == "/input/path"
    assert overrides["output_base_dir"] == "/output/path"
    assert overrides["output_subdir_name"] == "my_sub"
    assert overrides["output_prefix"] == "my_prefix"


def test_cli_defaults_are_not_in_overrides():
    """
    If arguments are not provided, they should NOT appear in overrides.
    This allows the underlying config.json to take precedence.
    """
    args = parse_args([])
    overrides = _args_to_overrides(args)

    # Keys should be missing or None, so merge_config ignores them
    assert "generate_tree" not in overrides
    assert "extensions" not in overrides
    assert overrides["input_path"] is None
    assert "process_modules" not in overrides
    assert "process_tests" not in overrides
    assert "create_unified_file" not in overrides
    assert "create_individual_files" not in overrides