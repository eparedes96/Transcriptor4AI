from __future__ import annotations

"""
Integration tests for the transcription pipeline.

Verifies the end-to-end flow, covering dry runs, parallel execution,
streaming-based transformations, and metadata validation for high-performance 
scenarios.
"""

import os
import pytest
from transcriptor4ai.pipeline import run_pipeline


@pytest.fixture
def source_structure(tmp_path):
    """
    Creates a temporary file structure for testing the pipeline:
    /src/main.py              (Contains mock secrets and comments)
    /src/utils.py
    /tests/test_main.py
    /ignored/__init__.py
    /docs/readme.md           (Resource)
    .gitignore                (Gitignore rule)
    secret.key                (Should be ignored if respect_gitignore=True)
    """
    src = tmp_path / "src"
    src.mkdir()

    (src / "main.py").write_text(
        "# Internal developer comment\n"
        "def main():\n"
        "    api_key = 'sk-1234567890abcdef1234567890abcdef'\n"
        "    pass",
        encoding="utf-8"
    )
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
# End-to-End Pipeline Tests
# -----------------------------------------------------------------------------

def test_pipeline_dry_run_behavior(source_structure):
    """Dry run should return OK but create no output files on disk."""
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

    # Verify final folder was NOT created or is empty
    out_dir = source_structure / "out"
    if out_dir.exists():
        assert len(list(out_dir.iterdir())) == 0


def test_pipeline_comprehensive_execution(source_structure):
    """
    End-to-end test verifying the V1.5.0 Parallel Engine:
    - Parallel Service Execution (Tree + Transcription)
    - Content Selection & Gitignore Filtering
    - Streaming Transformations (Sanitization + Minification)
    - Performance Metadata check
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
        "enable_sanitizer": True,
        "minify_output": True,
        "mask_user_paths": True,
        "create_individual_files": True,
        "create_unified_file": True,
        "generate_tree": True,
        "extensions": [".py", ".md", ".key"]
    }

    result = run_pipeline(config, dry_run=False)

    assert result.ok is True
    out_dir = source_structure / "full_run"
    assert out_dir.exists()

    # 1. Output Files Integrity
    assert (out_dir / "all_modules.txt").exists()
    assert (out_dir / "all_full_context.txt").exists()
    assert (out_dir / "all_tree.txt").exists()

    # 2. Content Validation (Filters & Gitignore)
    full_text = (out_dir / "all_full_context.txt").read_text(encoding="utf-8")
    assert "secret.key" not in full_text
    assert "SECRET_API_KEY" not in full_text
    assert "readme.md" in full_text

    # 3. Streaming Transformation Validation
    assert "sk-1234567890abcdef1234567890abcdef" not in full_text
    assert "[[REDACTED_SENSITIVE]]" in full_text
    assert "# Internal developer comment" not in full_text

    # 4. Performance Metadata
    assert result.token_count > 0
    perf_metrics = result.summary["V1.5_performance"]
    assert perf_metrics["parallel_engine"] is True
    assert perf_metrics["minifier"] is True


def test_pipeline_transformation_integrity(source_structure):
    """
    Verify that transformations can be disabled and the
    streaming output remains 'raw'.
    """
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "raw_run",
        "output_prefix": "raw",
        "enable_sanitizer": False,
        "minify_output": False,
        "mask_user_paths": False,
        "create_unified_file": True
    }

    result = run_pipeline(config, dry_run=False)
    assert result.ok is True

    content = (source_structure / "raw_run" / "raw_full_context.txt").read_text(encoding="utf-8")

    # Raw content should persist
    assert "sk-1234567890abcdef1234567890abcdef" in content
    assert "# Internal developer comment" in content


def test_pipeline_unified_only_flow(source_structure):
    """
    Verify staging logic: individual files should not be
    deployed if not requested.
    """
    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "unified_only",
        "output_prefix": "ctx",
        "create_individual_files": False,
        "create_unified_file": True,
        "generate_tree": True
    }

    result = run_pipeline(config, dry_run=False)
    assert result.ok is True

    out_dir = source_structure / "unified_only"
    assert not (out_dir / "ctx_modules.txt").exists()
    assert (out_dir / "ctx_full_context.txt").exists()


def test_pipeline_overwrite_protection(source_structure):
    """Ensure the pipeline respects existing files when overwrite is False."""
    out_dir = source_structure / "protect"
    out_dir.mkdir()
    (out_dir / "conflict_modules.txt").write_text("pre-existing content")

    config = {
        "input_path": str(source_structure),
        "output_base_dir": str(source_structure),
        "output_subdir_name": "protect",
        "output_prefix": "conflict",
        "create_individual_files": True
    }

    result = run_pipeline(config, overwrite=False)
    assert result.ok is False
    assert "existing files" in result.error.lower()