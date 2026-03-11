from __future__ import annotations

# ==============================================================================
# TEST GROUP: PROJECT SCANNER SERVICE
# ==============================================================================
import os
import re

import pytest

from transcriptor4ai.application.services.project_scanner import ProjectScannerService
from transcriptor4ai.domain.entities.transcription_error import TranscriptionError


@pytest.fixture
def scanner(mocker):
    """Provides a scanner instance with a mocked filesystem port."""
    mock_fs = mocker.Mock()
    # Mocking abspath to avoid Windows drive letters in tests
    mocker.patch("os.path.abspath", side_effect=lambda x: x.replace("\\", "/"))
    return ProjectScannerService(mock_fs)


@pytest.fixture
def mock_walk(mocker):
    """
    Simulates a directory tree structure for scanning.
    Note: We use forward slashes for consistency; the SUT should handle them.
    """
    return mocker.patch("os.walk", return_value=[
        ("/root", ["src", "tests"], ["README.md"]),
        ("/root/src", [], ["main.py", "utils.py"]),
        ("/root/tests", [], ["test_main.py"]),
    ])


@pytest.mark.unit
def test_yield_project_files_basic_classification(scanner, mock_walk):
    """
    Verifies that the scanner correctly identifies and classifies source modules,
    test suites, and resource files.
    """
    # 1. ARRANGE
    inc_rx = [re.compile(r".*")]
    exc_rx = []
    exts = [".py"]

    # 2. ACT
    files = list(scanner.yield_project_files(
        "/root", exts, inc_rx, exc_rx,
        process_modules=True, process_tests=True, process_resources=True
    ))

    # 3. ASSERT
    processed_files = [f for f in files if f["status"] == "process"]

    # Expected: main.py, utils.py, test_main.py, README.md
    assert len(processed_files) == 4

    filenames = [f["file_name"] for f in processed_files]
    assert "main.py" in filenames
    assert "test_main.py" in filenames
    assert "README.md" in filenames


@pytest.mark.unit
def test_yield_project_files_respects_exclusions(scanner, mock_walk):
    """
    Ensures that files matching exclusion regex patterns are marked as 'skipped'.
    We test exclusion by filename pattern to ensure it works regardless of os.walk pruning.
    """
    # 1. ARRANGE
    inc_rx = [re.compile(r".*")]
    # Exclude files that have 'test' in their name
    exc_rx = [re.compile(r"test_")]
    exts = [".py"]

    # 2. ACT
    files = list(scanner.yield_project_files(
        "/root", exts, inc_rx, exc_rx,
        process_modules=True, process_tests=True, process_resources=False
    ))

    # 3. ASSERT
    skipped_paths = [f["rel_path"] for f in files if f["status"] == "skipped"]

    # test_main.py should be explicitly skipped by the regex
    assert any("test_main.py" in p for p in skipped_paths)


@pytest.mark.unit
def test_prepare_filtering_rules_merges_gitignore(scanner, mocker):
    """
    Verifies that filtering rules aggregate default patterns and gitignore rules.
    """
    # 1. ARRANGE
    mock_git_loader = mocker.patch(
        "transcriptor4ai.application.services.project_scanner.load_gitignore_patterns",
        return_value=[r"build/.*"]
    )

    # 2. ACT
    inc, exc = scanner.prepare_filtering_rules(
        "/root",
        include_patterns=[r"\.py$"],
        exclude_patterns=[r"temp/.*"],
        respect_gitignore=True
    )

    # 3. ASSERT
    mock_git_loader.assert_called_once_with("/root")
    exc_patterns = [rx.pattern for rx in exc]
    assert r"temp/.*" in exc_patterns
    assert r"build/.*" in exc_patterns


@pytest.mark.unit
def test_finalize_error_reporting_delegates_to_filesystem(scanner, mocker):
    """
    Ensures OS-agnostic path handling for error reporting.
    """
    # 1. ARRANGE
    errors = [TranscriptionError(rel_path="src/main.py", error="I/O Failure")]
    error_path = "/out/errors.txt"

    # Mock 'open' to prevent actual disk write if the port call fails
    mocker.patch("builtins.open", mocker.mock_open())

    # 2. ACT
    scanner.finalize_error_reporting(save_error_log=True, error_output_path=error_path, errors=errors)

    # 3. ASSERT
    # We normalize both paths to avoid Windows/Unix mismatch (C:\out vs /out)
    call_path = os.path.normpath(scanner._fs.safe_mkdir.call_args[0][0])
    expected_path = os.path.normpath(os.path.dirname(error_path))

    assert call_path == expected_path


@pytest.mark.unit
def test_yield_project_files_skips_when_flags_are_disabled(scanner, mock_walk):
    """
    CRITICAL TEST: Verify that disabling process_tests correctly skips
    test files even if they match the .py extension.
    """
    # 1. ARRANGE
    inc_rx = [re.compile(r".*")]
    exc_rx = []
    exts = [".py"]  # Both modules and tests match this

    # 2. ACT: Disable tests
    files = list(scanner.yield_project_files(
        "/root", exts, inc_rx, exc_rx,
        process_modules=True, process_tests=False, process_resources=True
    ))

    # 3. ASSERT
    processed_names = [f["file_name"] for f in files if f["status"] == "process"]

    assert "main.py" in processed_names
    # This is where the SUT bug is detected: test_main.py MUST NOT be here
    assert "test_main.py" not in processed_names