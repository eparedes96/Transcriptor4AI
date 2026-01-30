from __future__ import annotations

# ==============================================================================
# TEST GROUP: CLI SYSTEM FLOW (E2E)
# ==============================================================================

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def run_transcriptor_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Helper to execute the application as a standalone subprocess.
    Ensures the 'src' directory is in PYTHONPATH.
    """
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "src"
    entry_point = src_path / "transcriptor4ai" / "main.py"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_path) + os.pathsep + env.get("PYTHONPATH", "")

    # Execute: python src/transcriptor4ai/main.py <args>
    return subprocess.run(
        [sys.executable, str(entry_point)] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd)
    )


@pytest.fixture
def sample_project_dir(tmp_path: Path) -> Path:
    """
    Creates a real directory structure with dummy code for E2E testing.
    """
    project = tmp_path / "my_app"
    project.mkdir()

    # Create source logic
    src = project / "src"
    src.mkdir()
    (src / "core.py").write_text("def business_logic(): pass", encoding="utf-8")

    # Create test
    tests = project / "tests"
    tests.mkdir()
    (tests / "test_core.py").write_text("def test_logic(): assert True", encoding="utf-8")

    # Create resource
    (project / "README.md").write_text("# Sample Project", encoding="utf-8")

    # Create .gitignore
    (project / ".gitignore").write_text("*.log\nnode_modules/", encoding="utf-8")
    (project / "error.log").write_text("should be ignored", encoding="utf-8")

    return project


@pytest.mark.e2e
def test_cli_full_execution_flow(sample_project_dir, tmp_path):
    """
    Verifies that running the CLI with standard arguments produces
    the expected output directory and artifacts.
    """
    # 1. ARRANGE
    output_base = tmp_path / "out"
    args = [
        "-i", str(sample_project_dir),
        "-o", str(output_base),
        "--subdir", "final_results",
        "--prefix", "e2e_test",
        "--tree",
        "--resources"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0

    final_dir = output_base / "final_results"
    assert final_dir.exists()

    # Verify mandatory artifacts existence
    expected_files = [
        "e2e_test_full_context.txt",
        "e2e_test_tree.txt",
        "e2e_test_modules.txt",
        "e2e_test_tests.txt",
        "e2e_test_resources.txt"
    ]

    for filename in expected_files:
        assert (final_dir / filename).exists(), f"Missing artifact: {filename}"

    # Verify content of the master context
    master_content = (final_dir / "e2e_test_full_context.txt").read_text(encoding="utf-8")
    assert "PROJECT CONTEXT: my_app" in master_content
    assert "business_logic" in master_content
    assert "test_logic" in master_content


@pytest.mark.e2e
def test_cli_dry_run_does_not_write_to_disk(sample_project_dir, tmp_path):
    """
    Ensures that the --dry-run flag performs logic/counting but
    bypasses all filesystem write operations.
    """
    # 1. ARRANGE
    output_base = tmp_path / "no_write_zone"
    args = [
        "-i", str(sample_project_dir),
        "-o", str(output_base),
        "--dry-run"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0
    assert "SIMULATION COMPLETE" in result.stdout
    # The output directory should never have been created
    assert not output_base.exists()


@pytest.mark.e2e
def test_cli_json_output_is_parseable(sample_project_dir, tmp_path):
    """
    Validates that the --json flag returns a valid JSON string
    representing the PipelineResult object.
    """
    # 1. ARRANGE
    args = [
        "-i", str(sample_project_dir),
        "--dry-run",
        "--json"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0

    # Attempt to parse stdout as JSON
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("CLI output with --json was not valid JSON")

    assert data["ok"] is True
    assert "summary" in data
    assert data["base_path"].endswith("my_app")


@pytest.mark.e2e
def test_cli_fails_on_invalid_input_path(tmp_path):
    """
    Verifies that the application exits with a non-zero code
    when pointing to a non-existent directory.
    """
    # 1. ARRANGE
    invalid_path = tmp_path / "the_void"
    args = ["-i", str(invalid_path)]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    # Should exit with error (usually code 2 for config/IO errors)
    assert result.returncode != 0
    assert "not exist" in result.stderr.lower()