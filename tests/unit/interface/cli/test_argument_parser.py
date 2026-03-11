from __future__ import annotations

# ==============================================================================
# TEST GROUP: CLI ARGUMENT PARSER
# ==============================================================================
import pytest

from transcriptor4ai.interface.cli.argument_parser import args_to_overrides, build_parser


def parse_args(arg_list: list[str]):
    """Helper to simulate CLI command line input parsing."""
    parser = build_parser()
    return parser.parse_args(arg_list)


@pytest.mark.unit
def test_parser_captures_path_arguments():
    """
    Verifies that basic path and naming arguments are correctly
    captured into the namespace.
    """
    # 1. ARRANGE
    cmd = [
        "-i", "/source/dir",
        "-o", "/output/base",
        "--subdir", "my_run",
        "--prefix", "custom"
    ]

    # 2. ACT
    args = parse_args(cmd)
    overrides = args_to_overrides(args)

    # 3. ASSERT
    assert overrides["input_path"] == "/source/dir"
    assert overrides["output_base_dir"] == "/output/base"
    assert overrides["output_subdir_name"] == "my_run"
    assert overrides["output_prefix"] == "custom"


@pytest.mark.unit
@pytest.mark.parametrize("flag, expected_depth", [
    ("--skeleton", "skeleton"),
    ("--no-modules", "tree_only")
])
def test_parser_maps_processing_depth_flags(flag, expected_depth):
    """
    Validates that v2.1 depth flags are correctly translated to
    the internal 'processing_depth' enumeration.
    """
    # 1. ARRANGE & 2. ACT
    args = parse_args([flag])
    overrides = args_to_overrides(args)

    # 3. ASSERT
    assert overrides["processing_depth"] == expected_depth
    if flag == "--no-modules":
        assert overrides["process_modules"] is False


@pytest.mark.unit
def test_parser_handles_csv_lists():
    """
    Ensures that comma-separated strings for extensions and patterns
    are parsed into clean Python lists.
    """
    # 1. ARRANGE
    cmd = [
        "--ext", ".py, .js, .ts",
        "--exclude", "node_modules, .git"
    ]

    # 2. ACT
    args = parse_args(cmd)
    overrides = args_to_overrides(args)

    # 3. ASSERT
    assert overrides["extensions"] == [".py", ".js", ".ts"]
    assert overrides["exclude_patterns"] == ["node_modules", ".git"]


@pytest.mark.unit
def test_parser_unified_only_logic():
    """
    Verifies the logical mapping of the '--unified-only' flag,
    which must affect two different internal settings.
    """
    # 1. ARRANGE & 2. ACT
    args = parse_args(["--unified-only"])
    overrides = args_to_overrides(args)

    # 3. ASSERT
    assert overrides["create_individual_files"] is False
    assert overrides["create_unified_file"] is True


@pytest.mark.unit
def test_parser_static_analysis_flags():
    """
    Validates that AST-related flags for the directory tree
    are correctly mapped.
    """
    # 1. ARRANGE
    cmd = ["--functions", "--classes", "--methods", "--tree"]

    # 2. ACT
    args = parse_args(cmd)
    overrides = args_to_overrides(args)

    # 3. ASSERT
    assert overrides["show_functions"] is True
    assert overrides["show_classes"] is True
    assert overrides["show_methods"] is True
    assert overrides["generate_tree"] is True


@pytest.mark.unit
def test_parser_preserves_unprovided_as_none():
    """
    CRITICAL: Unprovided arguments should result in None or missing keys
    in the overrides dict to avoid overwriting existing config.json settings.
    """
    # 1. ARRANGE: Empty command
    args = parse_args([])

    # 2. ACT
    overrides = args_to_overrides(args)

    # 3. ASSERT
    # Basic paths should be None in the namespace, and thus potentially
    # excluded or kept as None in overrides depending on implementation.
    assert overrides.get("input_path") is None
    # Booleans that use 'store_true' shouldn't even be in the overrides
    # if the parser code is written correctly to be additive.
    assert "minify_output" not in overrides
    assert "generate_tree" not in overrides