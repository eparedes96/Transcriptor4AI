from __future__ import annotations

# ==============================================================================
# TEST GROUP: PIPELINE RESULTS ENTITY
# ==============================================================================

import pytest
from dataclasses import FrozenInstanceError

from transcriptor4ai.domain.entities.pipeline_results import (
    PipelineResult,
    create_success_result,
    create_error_result
)


@pytest.fixture
def sample_trans_res():
    """Provides a sample transcription result summary from the engine."""
    return {
        "ok": True,
        "counters": {
            "processed": 5,
            "cached": 3,
            "skipped": 2,
            "errors": 0,
            "total_tokens": 1500
        },
        "generated": {
            "modules": "/tmp/out/modules.txt",
            "tests": "/tmp/out/tests.txt"
        }
    }


def test_create_success_result_populates_metrics(mock_config_dict, sample_trans_res):
    """
    Verifies that create_success_result correctly aggregates worker counters
    and configuration flags into the summary report.
    """
    # 1. ARRANGE
    base_path = "/src/project"
    final_path = "/out/transcript"

    # 2. ACT
    result = create_success_result(
        cfg=mock_config_dict,
        base_path=base_path,
        final_output_path=final_path,
        existing_files=["old_file.txt"],
        trans_res=sample_trans_res,
        tree_lines=["root", "  main.py"],
        token_count=sample_trans_res["counters"]["total_tokens"]
    )

    # 3. ASSERT
    assert result.ok is True
    assert result.token_count == 1500
    assert result.final_output_path == final_path

    # Check automated summary mapping
    summary = result.summary
    assert summary["processed"] == 5
    assert summary["V2.1_performance"]["cache_hits"] == 3
    assert summary["tree"]["lines"] == 2
    assert "old_file.txt" in summary["existing_files_before_run"]


def test_create_error_result_consistency(mock_config_dict):
    """
    Ensures create_error_result generates a valid PipelineResult object
    with consistent default values for missing data.
    """
    # 2. ACT
    error_msg = "Access Denied to /usr/bin"
    result = create_error_result(
        error=error_msg,
        cfg=mock_config_dict,
        base_path="/src/project"
    )

    # 3. ASSERT
    assert result.ok is False
    assert result.error == error_msg
    assert isinstance(result.existing_files, list)
    assert result.summary["status"] == "failed"
    # Essential for GUI: ensure it doesn't crash if these are missing
    assert result.token_count == 0


def test_pipeline_result_is_immutable(mock_config_dict):
    """
    The PipelineResult must be a frozen dataclass to guarantee
    thread-safety when passed between the Engine and the GUI.
    """
    # 1. ARRANGE
    result = create_error_result("Test Error", mock_config_dict, "/path")

    # 2. ACT & 3. ASSERT
    # Attempting to modify any field should raise FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        result.ok = True  # type: ignore


def test_success_result_generated_files_mapping(mock_config_dict, sample_trans_res):
    """
    Verify that the map of generated files is correctly preserved
    in the result summary.
    """
    # 1. ARRANGE
    generated = {"unified": "/path/to/full.txt"}

    # 2. ACT
    result = create_success_result(
        cfg=mock_config_dict,
        base_path="/in",
        final_output_path="/out",
        existing_files=[],
        trans_res=sample_trans_res,
        tree_lines=[],
        generated_files=generated
    )

    # 3. ASSERT
    assert result.summary["generated_files"]["unified"] == "/path/to/full.txt"