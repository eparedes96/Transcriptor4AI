from __future__ import annotations

"""
End-to-End (E2E) CLI Tests.

Verifies the application's external behavior by invoking the entry point
script via subprocess. These tests validate argument parsing, exit codes,
stream output (stdout/stderr), and file system side effects (artifact generation).
Alignment with 'processing_depth' configuration schema.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SRC_DIR = PROJECT_ROOT / "src"
ENTRY_POINT = SRC_DIR / "transcriptor4ai" / "main.py"


def run_cli(args: List[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """
    Helper to execute the CLI in a separate process.

    Injects the 'src' directory into PYTHONPATH to ensure the package
    is resolvable without being installed in site-packages.

    Args:
        args: List of command line arguments (excluding 'python' and script path).
        cwd: Optional working directory for the subprocess.

    Returns:
        subprocess.CompletedProcess: The result object containing returncode, stdout, and stderr.
    """
    env = os.environ.copy()
    env["PYTHONPATH"] = str(SRC_DIR) + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [sys.executable, str(ENTRY_POINT)] + args

    return subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8"
    )


@pytest.fixture
def sample_project(tmp_path: Path) -> Path:
    """
    Create a dummy project structure for E2E testing.

    Structure:
    /input
      /src
        main.py
      /tests
        test_main.py
      README.md
    """
    input_dir = tmp_path / "input"
    input_dir.mkdir()

    src_dir = input_dir / "src"
    src_dir.mkdir()
    (src_dir / "main.py").write_text("def main(): pass", encoding="utf-8")

    test_dir = input_dir / "tests"
    test_dir.mkdir()
    (test_dir / "test_main.py").write_text("def test_main(): assert True", encoding="utf-8")

    (input_dir / "README.md").write_text("# Dummy Project", encoding="utf-8")

    return input_dir


def test_cli_happy_path_execution(tmp_path: Path, sample_project: Path) -> None:
    """
    TC-01: Verify a standard execution produces expected artifacts (Exit Code 0).
    """
    output_dir = tmp_path / "output"

    args = [
        "-i", str(sample_project),
        "-o", str(output_dir),
        "--prefix", "e2e_test",
        "--subdir", "results",
        "--tree",
        "--resources"
    ]

    result = run_cli(args)

    # 1. Check Exit Code
    assert result.returncode == 0, f"CLI failed with stderr: {result.stderr}"

    # 2. Check File Side Effects
    target_dir = output_dir / "results"
    assert target_dir.exists(), "Output subdirectory was not created."

    expected_files = [
        "e2e_test_modules.txt",
        "e2e_test_tests.txt",
        "e2e_test_resources.txt",
        "e2e_test_tree.txt",
        "e2e_test_full_context.txt"
    ]

    for filename in expected_files:
        assert (target_dir / filename).exists(), f"Artifact {filename} missing."


def test_cli_handles_missing_input(tmp_path: Path) -> None:
    """
    TC-02: Verify CLI returns error code 2 (or 1) when input path is invalid.
    """
    missing_path = tmp_path / "non_existent_folder"

    args = ["-i", str(missing_path), "-o", str(tmp_path)]

    result = run_cli(args)

    assert result.returncode != 0
    assert "does not exist" in result.stderr or "Input path does not exist" in result.stderr


def test_cli_dry_run_simulation(tmp_path: Path, sample_project: Path) -> None:
    """
    TC-03: Verify 'dry-run' mode does not write to disk but reports success.
    """
    output_dir = tmp_path / "output_dry"

    args = [
        "-i", str(sample_project),
        "-o", str(output_dir),
        "--dry-run"
    ]

    result = run_cli(args)

    assert result.returncode == 0
    assert "SIMULATION COMPLETE" in result.stdout

    # Ensure no physical files were created
    assert not output_dir.exists(), "Dry run should not create output directories."


def test_cli_config_overrides(tmp_path: Path, sample_project: Path) -> None:
    """
    TC-04: Verify command line flags override default configuration values.

    Uses --json output to inspect the internal configuration state used during run.
    """
    output_dir = tmp_path / "output_override"

    args = [
        "-i", str(sample_project),
        "-o", str(output_dir),
        "--no-modules",
        "--no-tests",
        "--json",
        "--dry-run"
    ]

    result = run_cli(args)
    assert result.returncode == 0

    try:
        data: Dict[str, Any] = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail(f"Failed to decode JSON output: {result.stdout}")

    # Check that flags were respected in the pipeline result
    assert data["ok"] is True
    assert data["processing_depth"] == "tree_only"
    assert data["process_tests"] is False
    assert data["process_resources"] is True


def test_cli_json_output_structure(tmp_path: Path, sample_project: Path) -> None:
    """
    TC-05: Verify structure and content of JSON output mode.
    """
    output_dir = tmp_path / "output_json"

    args = [
        "-i", str(sample_project),
        "-o", str(output_dir),
        "--json",
        "--dry-run"
    ]

    result = run_cli(args)
    assert result.returncode == 0

    data = json.loads(result.stdout)

    # Validate Schema Root
    required_keys = [
        "ok", "error", "base_path", "final_output_path",
        "token_count", "summary"
    ]
    for key in required_keys:
        assert key in data, f"JSON output missing key: {key}"
    assert "generated_files" in data["summary"], "generated_files missing from summary"

    # Validate Content
    assert data["base_path"] == str(sample_project.resolve())
    assert "dry_run" in data["summary"]
    assert data["summary"]["dry_run"] is True


def test_cli_help_message() -> None:
    """
    TC-06: Verify help message is displayed (smoke test for argparse).
    """
    result = run_cli(["--help"])

    assert result.returncode == 0
    assert "usage: transcriptor4ai" in result.stdout
    assert "--input" in result.stdout