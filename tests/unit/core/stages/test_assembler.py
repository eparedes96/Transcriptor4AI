from __future__ import annotations

"""
Unit tests for the Pipeline Assembler.

Verifies artifact merging, token estimation, and staging-to-final atomic deployment.
"""

import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from transcriptor4ai.core.pipeline.stages.assembler import assemble_and_finalize


@pytest.fixture
def env_context(tmp_path: Path) -> dict:
    """Provides a dummy execution environment context."""
    staging = tmp_path / "staging"
    staging.mkdir()
    final = tmp_path / "final"
    final.mkdir()

    # Create dummy staging files
    (staging / "t_modules.txt").write_text("MOD_CONTENT", encoding="utf-8")
    (staging / "t_tree.txt").write_text("TREE_CONTENT", encoding="utf-8")

    return {
        "base_path": "/project",
        "final_output_path": str(final),
        "staging_dir": str(staging),
        "temp_dir_obj": None,
        "prefix": "t",
        "paths": {
            "modules": str(staging / "t_modules.txt"),
            "tree": str(staging / "t_tree.txt"),
            "unified": str(staging / "t_full_context.txt"),
            "errors": str(staging / "t_errors.txt")
        },
        "existing_files": [],
        "files_to_check": []
    }


def test_assemble_and_finalize_merging(env_context: dict) -> None:
    """TC-01: Verify that staging files are merged correctly into the unified file."""
    cfg = {
        "create_unified_file": True,
        "create_individual_files": True,
        "generate_tree": True,
        "target_model": "GPT-4o"
    }
    trans_res = {
        "ok": True,
        "generated": {"modules": env_context["paths"]["modules"]},
        "counters": {"processed": 1}
    }

    with patch("transcriptor4ai.core.pipeline.stages.assembler.count_tokens", return_value=123):
        result = assemble_and_finalize(cfg, trans_res, ["line1"], env_context, dry_run=False)

        assert result.ok is True
        assert result.token_count == 123

        # Check unified file content in final path
        final_unified = Path(env_context["final_output_path"]) / "t_full_context.txt"
        assert final_unified.exists()
        content = final_unified.read_text(encoding="utf-8")
        assert "MOD_CONTENT" in content
        assert "PROJECT STRUCTURE" in content


def test_assemble_dry_run_no_move(env_context: dict) -> None:
    """TC-03: Verify that dry_run skips moving files from staging to final."""
    cfg = {"create_unified_file": True, "create_individual_files": True}
    trans_res = {"ok": True, "generated": {}, "counters": {}}

    result = assemble_and_finalize(cfg, trans_res, [], env_context, dry_run=True)

    final_dir = Path(env_context["final_output_path"])
    assert len(list(final_dir.iterdir())) == 0, "Dry run should not write to final path."