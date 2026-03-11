from __future__ import annotations

import re

import pytest

from transcriptor4ai.application.pipeline.components.file_filters import (
    _gitignore_to_regex,
    compile_patterns,
    default_exclude_patterns,
    default_extensions,
    default_include_patterns,
    determine_target_mode,
    is_resource_file,
    is_test,
    load_gitignore_patterns,
    matches_any,
    matches_include,
)

# ==============================================================================
# TEST GROUP: DEFAULTS & COMPILATION
# ==============================================================================

@pytest.mark.unit
def test_default_factories_return_populated_lists():
    # 1. ARRANGE & ACT
    exts = default_extensions()
    incs = default_include_patterns()
    excs = default_exclude_patterns()

    # 3. ASSERT
    assert isinstance(exts, list)
    assert ".py" in exts
    assert isinstance(incs, list)
    assert ".*" in incs
    assert isinstance(excs, list)
    assert len(excs) > 0


@pytest.mark.unit
def test_compile_patterns_should_return_valid_regex_objects():
    # 1. ARRANGE
    raw_patterns = [r"^test_.*\.py$", r".*\.js$"]

    # 2. ACT
    compiled = compile_patterns(raw_patterns)

    # 3. ASSERT
    assert len(compiled) == 2
    assert all(isinstance(p, re.Pattern) for p in compiled)


@pytest.mark.unit
def test_compile_patterns_should_silently_ignore_malformed_regex():
    # 1. ARRANGE
    raw_patterns = [r"^valid_.*$", r"[invalid_unclosed_bracket"]

    # 2. ACT
    compiled = compile_patterns(raw_patterns)

    # 3. ASSERT
    # Ensures the application doesn't crash on bad user input
    assert len(compiled) == 1
    assert compiled[0].pattern == r"^valid_.*$"


# ==============================================================================
# TEST GROUP: MATCHING LOGIC
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("filename, expected", [
    ("test_module.py", True),
    ("__pycache__", True),
    ("clean_module.py", False),
    ("node_modules", True)
])
def test_matches_any_evaluates_against_multiple_patterns(filename, expected):
    # 1. ARRANGE
    patterns = compile_patterns([r"^test_.*", r"^__pycache__$", r"^node_modules$"])

    # 2. ACT
    result = matches_any(filename, patterns)

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
@pytest.mark.parametrize("filename, expected", [
    ("api_controller.py", True),
    ("secret_keys.env", False)
])
def test_matches_include_evaluates_whitelist(filename, expected):
    # 1. ARRANGE
    patterns = compile_patterns([r".*\.py$"])

    # 2. ACT
    result = matches_include(filename, patterns)

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
def test_matches_include_returns_false_when_patterns_list_is_empty():
    # 1. ARRANGE
    empty_patterns = []

    # 2. ACT
    result = matches_include("any_file.py", empty_patterns)

    # 3. ASSERT
    assert result is False


# ==============================================================================
# TEST GROUP: FILE CLASSIFICATION
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("filename, expected", [
    # Happy Paths (Polyglot conventions)
    ("test_calculator.py", True),
    ("calculator_test.js", True),
    ("AppTest.java", True),
    ("TestRunner.cs", True),
    ("app.spec.ts", True),
    ("login.e2e.js", True),
    ("button.cy.tsx", True),
    # Sad Paths (Not actual tests or unsupported extensions)
    ("test.txt", False),
    ("testing_utils.py", False),
    ("my_test_framework.py", False),
    ("attest.py", False)
])
def test_is_test_identifies_test_suites_across_languages(filename, expected):
    # 1. ARRANGE & ACT
    result = is_test(filename)

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
@pytest.mark.parametrize("filename, expected", [
    # Standard resource files
    ("Dockerfile", True),
    ("Makefile", True),
    (".gitignore", True),
    ("config.yaml", True),
    ("settings.json", True),
    ("README.md", True),
    ("styles.css", True),
    # Standard source logic files
    ("main.py", False),
    ("app.js", False),
    ("Controller.java", False)
])
def test_is_resource_file_identifies_non_code_assets(filename, expected):
    # 1. ARRANGE & ACT
    result = is_resource_file(filename)

    # 3. ASSERT
    assert result == expected


# ==============================================================================
# TEST GROUP: TARGET MODE DETERMINATION
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "file_name, depth, proc_tests, proc_res, expected_mode", [
        # Tree Only mode overrides everything
        ("main.py", "tree_only", True, True, "skip"),
        # Test Files Logic
        ("test_calc.py", "full", True, False, "test"),
        ("test_calc.py", "full", False, False, "skip"),
        # Resource Files Logic
        ("config.json", "full", False, True, "resource"),
        ("config.json", "full", False, False, "module"),  # Defaults to module if resources disabled
        # Standard Code Modules
        ("main.py", "full", True, True, "module"),
        ("main.py", "skeleton", True, True, "module"),
    ]
)
def test_determine_target_mode_enforces_domain_policies(
        file_name, depth, proc_tests, proc_res, expected_mode
):
    # 1. ARRANGE & ACT
    mode = determine_target_mode(file_name, depth, proc_tests, proc_res)

    # 3. ASSERT
    assert mode == expected_mode


# ==============================================================================
# TEST GROUP: GITIGNORE PARSING
# ==============================================================================

@pytest.mark.unit
def test_load_gitignore_patterns_parses_valid_file(mocker):
    # 1. ARRANGE: Prepare mock file content with comments and empty lines
    mock_content = """
    # This is a comment

    node_modules/
    *.log
    .env
    """
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=mock_content))

    # 2. ACT
    patterns = load_gitignore_patterns("/fake/root")

    # 3. ASSERT
    # Expecting 3 parsed patterns (node_modules, *.log, .env)
    assert len(patterns) == 3
    assert any("node_modules" in p for p in patterns)
    assert any(".env" in p for p in patterns)


@pytest.mark.unit
def test_load_gitignore_patterns_returns_empty_list_if_file_missing(mocker):
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=False)

    # 2. ACT
    patterns = load_gitignore_patterns("/fake/root")

    # 3. ASSERT
    assert patterns == []


@pytest.mark.unit
def test_load_gitignore_patterns_recovers_gracefully_from_io_error(mocker):
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", side_effect=PermissionError("Access denied"))

    # 2. ACT
    patterns = load_gitignore_patterns("/fake/root")

    # 3. ASSERT
    # Should not crash the pipeline, just return empty list
    assert patterns == []


@pytest.mark.unit
@pytest.mark.parametrize("glob_input, expected_regex_fragment", [
    ("*.log", r"\.log"),
    ("build/", r"build"),
    ("temp*", r"temp.*")
])
def test_gitignore_to_regex_translation(glob_input, expected_regex_fragment):
    # 1. ARRANGE & ACT
    regex = _gitignore_to_regex(glob_input)

    # 3. ASSERT
    assert expected_regex_fragment in regex