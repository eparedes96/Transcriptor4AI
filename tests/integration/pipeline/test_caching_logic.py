from __future__ import annotations

"""
Integration tests for the Pipeline Caching Logic.

Verifies that the CacheService correctly identifies unchanged files across 
multiple runs and that configuration changes (sanitizer, minification) 
properly invalidate the cache to ensure data consistency.
"""

from pathlib import Path
from typing import Any, Dict

import pytest

from transcriptor4ai.core.pipeline.stages.transcriber import transcribe_code
from transcriptor4ai.core.services.cache import CacheService


@pytest.fixture
def workspace(tmp_path: Path) -> Dict[str, Any]:
    """Create a temporary workspace with source files for caching tests."""
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    (input_dir / "logic.py").write_text("def run():\n    return 42", encoding="utf-8")
    (input_dir / "utils.py").write_text("def help():\n    pass", encoding="utf-8")

    return {
        "input": str(input_dir),
        "output": output_dir,
        "mod_path": str(output_dir / "mod.txt"),
        "err_path": str(output_dir / "err.txt")
    }


def test_cache_hit_and_miss_lifecycle(workspace: Dict[str, Any]) -> None:
    """
    TC-01: Verify that the second run results in 100% cache hits.
    """
    cache_service = CacheService()
    cache_service.purge_all()

    params = {
        "input_path": workspace["input"],
        "modules_output_path": workspace["mod_path"],
        "tests_output_path": str(workspace["output"] / "test.txt"),
        "resources_output_path": str(workspace["output"] / "res.txt"),
        "error_output_path": workspace["err_path"],
        "minify_output": False
    }

    # 1. First Run (Cold Start)
    res1 = transcribe_code(**params)
    assert res1["ok"] is True
    assert res1["counters"]["processed"] == 2
    assert res1["counters"]["cached"] == 0

    # 2. Second Run (Warm Start - No changes)
    res2 = transcribe_code(**params)
    assert res2["ok"] is True
    assert res2["counters"]["processed"] == 2
    assert res2["counters"]["cached"] == 2


def test_cache_invalidation_on_config_change(workspace: Dict[str, Any]) -> None:
    """
    TC-02: Verify that changing a config flag invalidates the cache.
    """
    cache_service = CacheService()
    cache_service.purge_all()

    base_params = {
        "input_path": workspace["input"],
        "modules_output_path": workspace["mod_path"],
        "tests_output_path": str(workspace["output"] / "test.txt"),
        "resources_output_path": str(workspace["output"] / "res.txt"),
        "error_output_path": workspace["err_path"],
    }

    # 1. Run with Minify OFF
    transcribe_code(**base_params, minify_output=False)

    # 2. Run with Minify ON (Should be a CACHE MISS even if files are same)
    res = transcribe_code(**base_params, minify_output=True)
    assert res["counters"]["cached"] == 0, "Cache should have been invalidated by config change"