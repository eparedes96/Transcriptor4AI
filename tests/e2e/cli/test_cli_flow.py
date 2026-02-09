from __future__ import annotations

# ==============================================================================
# TEST GROUP: CLI SYSTEM FLOW (E2E)
# ==============================================================================

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


def run_transcriptor_cli(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """
    Helper to execute the application as a standalone subprocess.
    Ensures the 'src' directory is in PYTHONPATH to allow internal imports.
    """
    project_root = Path(__file__).parent.parent.parent.parent
    src_path = project_root / "src"
    entry_point = src_path / "transcriptor4ai" / "main.py"

    env = os.environ.copy()
    env["PYTHONPATH"] = str(src_path) + os.pathsep + env.get("PYTHONPATH", "")

    return subprocess.run(
        [sys.executable, str(entry_point)] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(cwd)
    )


@pytest.fixture
def prepared_project_path(sample_project_source: Path, tmp_path: Path) -> Path:
    """
    Clones the static 'sample_project' into a temporary directory.
    This ensures each test works on a fresh copy of the real data.
    """
    target_path = tmp_path / "integration_project"
    shutil.copytree(sample_project_source, target_path)
    return target_path


@pytest.mark.e2e
def test_cli_full_execution_flow(prepared_project_path, tmp_path):
    """
    Verifies that running the CLI against the real sample project produces
    all expected artifacts with valid architectural content.
    """
    # 1. ARRANGE
    output_base = tmp_path / "out"
    args = [
        "-i", str(prepared_project_path),
        "-o", str(output_base),
        "--subdir", "e2e_results",
        "--prefix", "full_test",
        "--tree",
        "--resources",
        "--classes",
        "--functions"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0, f"CLI Failed: {result.stderr}"

    final_dir = output_base / "e2e_results"
    assert final_dir.exists()

    expected_files = [
        "full_test_full_context.txt",
        "full_test_tree.txt",
        "full_test_modules.txt",
        "full_test_tests.txt",
        "full_test_resources.txt"
    ]

    for filename in expected_files:
        assert (final_dir / filename).exists(), f"Missing artifact: {filename}"

    master_content = (final_dir / "full_test_full_context.txt").read_text(encoding="utf-8")
    assert "PROJECT CONTEXT: integration_project" in master_content
    assert "Class: Calculator" in master_content
    assert "Function: format_currency" in master_content


@pytest.mark.e2e
def test_cli_dry_run_does_not_write_to_disk(prepared_project_path, tmp_path):
    """
    Ensures that simulation mode (--dry-run) performs logic calculations
    but creates NO files on the filesystem.
    """
    # 1. ARRANGE
    output_base = tmp_path / "forbidden_zone"
    args = [
        "-i", str(prepared_project_path),
        "-o", str(output_base),
        "--dry-run"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0
    # Validamos que el mensaje de éxito esté en stdout
    assert "SIMULATION COMPLETE" in result.stdout

    # CRITICAL FIX: Las estadísticas del motor se envían a stderr mediante logging.INFO
    # Buscamos la confirmación de que el Transcriber trabajó, pero en el flujo de error estándar.
    assert "Processed:" in result.stderr
    assert "Transcriber: Cycle complete" in result.stderr

    # Aseguramos que físicamente no se creó nada
    assert not output_base.exists()


@pytest.mark.e2e
def test_cli_json_output_is_parseable(prepared_project_path, tmp_path):
    """
    Validates that the --json flag returns a machine-parsable JSON.
    """
    # 1. ARRANGE
    args = [
        "-i", str(prepared_project_path),
        "--dry-run",
        "--json"
    ]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode == 0
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        pytest.fail("CLI output with --json was not valid JSON")

    assert data["ok"] is True
    assert "summary" in data
    assert data["base_path"].endswith("integration_project")


@pytest.mark.e2e
def test_cli_fails_on_invalid_input_path(tmp_path):
    """
    Verifies that the CLI identifies non-existent directories.
    """
    # 1. ARRANGE
    invalid_path = tmp_path / "ghost_directory"
    args = ["-i", str(invalid_path)]

    # 2. ACT
    result = run_transcriptor_cli(args, tmp_path)

    # 3. ASSERT
    assert result.returncode != 0
    assert "not exist" in result.stderr.lower()