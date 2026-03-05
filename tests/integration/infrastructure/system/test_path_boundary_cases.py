from __future__ import annotations

import os
import pytest
from pathlib import Path

from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter


# ==============================================================================
# TEST GROUP: PATH RESOLUTION AND BOUNDARY CASES
# ==============================================================================

@pytest.fixture
def fs() -> FileSystemAdapter:
    """Provides a fresh instance of the FileSystemAdapter."""
    return FileSystemAdapter()


@pytest.mark.integration
def test_normalize_path_expands_home_and_env_variables(fs, mocker, tmp_path):
    """
    Verifies that the path normalizer correctly expands user home directories (~)
    and custom environment variables into absolute paths.
    """
    # 1. ARRANGE: Set up a controlled environment variable and home directory
    test_env_dir = str(tmp_path / "env_folder")
    mocker.patch.dict(os.environ, {"MY_TEST_VAR": test_env_dir})

    fake_home = str(tmp_path / "home")
    mocker.patch("os.path.expanduser", lambda x: x.replace("~", fake_home))
    mocker.patch("os.path.expandvars", lambda x: x.replace("$MY_TEST_VAR", test_env_dir))

    # 2. ACT: Normalize paths containing boundary shortcuts
    home_path = fs.normalize_path("~/projects", fallback="/tmp")
    env_path = fs.normalize_path("$MY_TEST_VAR/src", fallback="/tmp")

    # 3. ASSERT: Shortcuts are expanded to absolute paths
    assert home_path == os.path.abspath(f"{fake_home}/projects")
    assert env_path == os.path.abspath(f"{test_env_dir}/src")


@pytest.mark.integration
@pytest.mark.parametrize("bad_input", [None, "", "   ", "\n\t"])
def test_normalize_path_handles_empty_or_null_inputs_using_fallback(fs, bad_input, tmp_path):
    """
    Ensures that empty strings, whitespace-only strings, or None values
    gracefully trigger the fallback mechanism to prevent OS TypeErrors.
    """
    # 1. ARRANGE: Define a valid absolute fallback path
    fallback_dir = str(tmp_path / "safe_fallback")

    # 2. ACT: Call normalization with boundary inputs
    result = fs.normalize_path(bad_input, fallback_dir)

    # 3. ASSERT: The system defaulted to the fallback securely
    assert result == os.path.abspath(fallback_dir)


@pytest.mark.integration
@pytest.mark.parametrize("bad_subdir", [None, "", "    "])
def test_get_real_output_path_uses_default_when_subdir_is_blank(fs, bad_subdir, tmp_path):
    """
    Validates that creating the final output directory path falls back to the
    domain default ('transcript') if the user provided an empty or null subdirectory.
    """
    # 1. ARRANGE: Base output directory
    base_dir = str(tmp_path / "out")

    # 2. ACT: Attempt to resolve with invalid subdirectories
    result = fs.get_real_output_path(base_dir, bad_subdir)

    # 3. ASSERT: The default folder name 'transcript' is forcefully appended
    expected_path = os.path.join(base_dir, "transcript")
    assert result == expected_path


@pytest.mark.integration
def test_build_staging_paths_with_unicode_and_spaces(fs):
    """
    Ensures that path assembly works perfectly when the directory or prefix
    contains emojis, spaces, and non-ASCII characters.
    """
    # 1. ARRANGE: Setup boundary strings
    staging_dir = "/tmp/Ruta de Prueba/🚀_Español"
    prefix = "P@th 123_Á"

    # 2. ACT: Build the artifact map
    paths = fs.build_staging_paths(staging_dir, prefix)

    # 3. ASSERT: All keys exist and strings are concatenated correctly
    assert "modules" in paths
    assert paths["modules"] == os.path.join(staging_dir, f"{prefix}_modules.txt")
    assert paths["errors"] == os.path.join(staging_dir, f"{prefix}_errors.txt")


@pytest.mark.integration
def test_get_expected_filenames_handles_edge_prefixes(fs):
    """
    Verifies that the filename generator constructs the correct list
    even if the user-defined prefix is incredibly long or contains symbols.
    """
    # 1. ARRANGE: Create a config that requests all files, and a very long prefix
    cfg = {
        "create_individual_files": True,
        "process_modules": True,
        "process_tests": True,
        "process_resources": True,
        "generate_tree": True,
        "create_unified_file": True,
        "save_error_log": True
    }
    edge_prefix = "A" * 150 + "---"

    # 2. ACT: Generate expected names
    filenames = fs.get_expected_filenames(cfg, edge_prefix)

    # 3. ASSERT: The correct number of files is generated with the exact prefix
    assert len(filenames) == 6
    assert f"{edge_prefix}_modules.txt" in filenames
    assert f"{edge_prefix}_full_context.txt" in filenames
    assert f"{edge_prefix}_errors.txt" in filenames