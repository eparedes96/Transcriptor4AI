from __future__ import annotations

"""
Integration tests for the transcription pipeline.

Verifies the end-to-end flow, covering dry runs, full execution with 
modern features (Resources, Gitignore, Tokens), and configuration flexibility.
"""

import os
import pytest
from transcriptor4ai.pipeline import run_pipeline


@pytest.fixture
def source_structure(tmp_path):
    """
    Creates a temporary file structure for testing the pipeline:
    /src/main.py
    /src/utils.py
    /tests/test_main.py
    /ignored/__init__.py
    /docs/readme.md           (Resource)
    .gitignore                (Gitignore rule)
    secret.key                (Should be ignored if respect_gitignore=True)
    """
    src = tmp_path / "src"
    src.mkdir()
    (src / "main.py").write_text("def main(): pass", encoding="utf-8")
    (src / "utils.py").write_text("class Utils: pass", encoding="utf-8")
    (src / "__init__.py").write_text("", encoding="utf-8")

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_main.py").write_text("def test_one(): pass", encoding="utf-8")

    # Resource file
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "readme.md").write_text("# Documentation", encoding="utf-8")

    # Gitignore and ignored file
    (tmp_path / ".gitignore").write_text("*.key", encoding="utf-8")
    (tmp_path / "secret.key").write_text("SECRET_API_KEY", encoding="utf-8")

    return tmp_path


# -----------------------------------------------------------------------------
# Integration Tests
# -----------------------------------------------------------------------------

def test_pipeline_dry_run_does_not_write(source_structure):
    """Dry run should return OK but create no output files."""
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "out",
        "output_prefix": "dry",
        "process_modules": True,
        "create_individual_files": True
    }

    result = run_pipeline(config, dry_run=True)

    assert result.ok is True
    assert result.summary["dry_run"] is True

    # Verify folder was NOT created or is empty
    out_dir = source_structure / "out"
    if out_dir.exists():
        assert len(list(out_dir.iterdir())) == 0


def test_pipeline_comprehensive_execution(source_structure):
    """
    Test:
    - Modules + Tests + Resources enabled.
    - Gitignore active (should exclude secret.key).
    - Tree generation.
    - Token counting.
    - Unified file assembly.
    """
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "full_run",
        "output_prefix": "all",
        "process_modules": True,
        "process_tests": True,
        "process_resources": True,
        "respect_gitignore": True,
        "create_individual_files": True,
        "create_unified_file": True,
        "generate_tree": True,
        "extensions": [".py", ".md", ".key"]
    }

    result = run_pipeline(config, dry_run=False)

    assert result.ok is True
    out_dir = source_structure / "full_run"
    assert out_dir.exists()

    # 1. Check Output Files Existence
    assert (out_dir / "all_modules.txt").exists()
    assert (out_dir / "all_tests.txt").exists()
    assert (out_dir / "all_resources.txt").exists()
    assert (out_dir / "all_tree.txt").exists()
    assert (out_dir / "all_full_context.txt").exists()

    # 2. Check Gitignore Logic (secret.key must be absent)
    full_text = (out_dir / "all_full_context.txt").read_text(encoding="utf-8")
    assert "secret.key" not in full_text
    assert "SECRET_API_KEY" not in full_text

    # 3. Check Resource Logic (readme.md must be present)
    assert "readme.md" in full_text
    assert "# Documentation" in full_text

    # 4. Check Token Count
    assert result.token_count > 0
    assert isinstance(result.token_count, int)


def test_pipeline_selective_config_behavior(source_structure):
    """
    Test configuration flexibility (Simulate "Legacy" or "Unsafe" mode):
    - NO Resources (should not generate _resources.txt).
    - NO Gitignore (should INCLUDE secret.key).
    """
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "unsafe_run",
        "output_prefix": "unsafe",
        "process_modules": True,
        "process_tests": True,
        "process_resources": False,
        "respect_gitignore": False,
        "create_individual_files": True,
        "create_unified_file": True
    }

    result = run_pipeline(config, dry_run=False)
    assert result.ok is True
    out_dir = source_structure / "unsafe_run"

    # 1. Check Resources are missing
    assert not (out_dir / "unsafe_resources.txt").exists()

    full_text = (out_dir / "unsafe_full_context.txt").read_text(encoding="utf-8")
    assert "RESOURCES (CONFIG/DATA/DOCS):" not in full_text

    # 2. Check Gitignore ignored (secret.key MUST be present)
    config["extensions"] = [".py", ".key"]
    result = run_pipeline(config, overwrite=True)
    full_text = (out_dir / "unsafe_full_context.txt").read_text(encoding="utf-8")

    assert "secret.key" in full_text
    assert "SECRET_API_KEY" in full_text


def test_pipeline_unified_only(source_structure):
    """
    Test the scenario where user wants ONLY the unified file.
    This verifies the tempfile staging logic in the pipeline.
    """
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "unified_only",
        "output_prefix": "ctx",
        "process_modules": True,
        "process_tests": True,
        "create_individual_files": False,
        "create_unified_file": True,
        "generate_tree": True
    }

    result = run_pipeline(config, dry_run=False)
    assert result.ok is True

    out_dir = source_structure / "unified_only"

    # Assert individual files do NOT exist
    assert not (out_dir / "ctx_modules.txt").exists()
    assert not (out_dir / "ctx_tests.txt").exists()
    assert not (out_dir / "ctx_tree.txt").exists()

    # Assert unified file DOES exist
    unified_file = out_dir / "ctx_full_context.txt"
    assert unified_file.exists()

    # Assert content is correct
    content = unified_file.read_text(encoding="utf-8")
    assert "PROJECT CONTEXT" in content

    # Fix for Windows: Check for either forward or backward slash
    assert "src/main.py" in content or "src\\main.py" in content


def test_pipeline_overwrite_protection(source_structure):
    """Pipeline should fail if files exist and overwrite is False."""
    out_dir = source_structure / "protect"
    out_dir.mkdir()

    # Create a conflict file that matches the target individual file
    (out_dir / "conflict_modules.txt").write_text("exists")

    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "protect",
        "output_prefix": "conflict",
        "create_individual_files": True,
        "process_modules": True
    }

    # First run: Should fail (ok=False) because file exists
    result = run_pipeline(config, overwrite=False)
    assert result.ok is False
    assert "existing files" in result.error.lower() or "existing_files" in result.summary

    # Second run: Should succeed with overwrite=True
    result_force = run_pipeline(config, overwrite=True)
    assert result_force.ok is True