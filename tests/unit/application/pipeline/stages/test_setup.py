from __future__ import annotations

"""
Unit tests for the Pipeline Setup stage.

Validates path normalization, staging area initialization, and collision detection.
"""

from pathlib import Path

from transcriptor4ai.core.pipeline.stages.setup import prepare_environment


def test_prepare_environment_invalid_input(tmp_path: Path) -> None:
    """TC-01: Verify that non-existent input directory returns an error result."""
    cfg = {"input_path": str(tmp_path / "void")}
    result, context = prepare_environment(
        cfg, overwrite=False, dry_run=False, tree_output_path=None
    )

    assert result is not None
    assert result.ok is False
    assert "Invalid or non-existent" in result.error


def test_prepare_environment_collision_detection(tmp_path: Path) -> None:
    """TC-02: Verify that existing files trigger a collision error if overwrite is False."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    # Create a colliding file
    (output_dir / "transcript_full_context.txt").write_text("exists")

    cfg = {
        "input_path": str(input_dir),
        "output_base_dir": str(tmp_path),
        "output_subdir_name": "out",
        "output_prefix": "transcript",
        "create_unified_file": True,
        "create_individual_files": False,
        "process_modules": True,
        "process_tests": False,
        "process_resources": False,
        "generate_tree": False,
        "save_error_log": False
    }

    result, context = prepare_environment(
        cfg, overwrite=False, dry_run=False, tree_output_path=None
    )

    assert result is not None
    assert "Naming collision detected" in result.error
    assert len(result.existing_files) > 0


def test_prepare_environment_staging_logic(tmp_path: Path) -> None:
    """TC-03: Verify that dry_run initializes a temporary staging directory."""
    input_dir = tmp_path / "in"
    input_dir.mkdir()

    cfg = {
        "input_path": str(input_dir),
        "output_base_dir": str(tmp_path / "out"),
        "output_subdir_name": "results",
        "output_prefix": "p",
        "create_individual_files": False,
        "create_unified_file": True,
        "process_modules": True,
        "process_tests": False,
        "process_resources": False,
        "generate_tree": False,
        "save_error_log": False
    }

    result, context = prepare_environment(
        cfg, overwrite=True, dry_run=True, tree_output_path=None
    )

    assert result is None
    assert context["temp_dir_obj"] is not None
    assert "tmp" in context["staging_dir"].lower()