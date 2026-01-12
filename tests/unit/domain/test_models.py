from __future__ import annotations

"""
Unit tests for Domain Models.

Verifies:
1. Data integrity of PipelineResult factories (Success/Error).
2. Immutability of frozen dataclasses.
3. Default values in domain objects.
"""

from transcriptor4ai.domain.pipeline_models import (
    create_success_result,
    create_error_result,
    PipelineResult
)
from transcriptor4ai.domain.transcription_models import TranscriptionError
from transcriptor4ai.domain.tree_models import FileNode


def test_create_success_result_populates_fields(mock_config_dict):
    """
    Verify that the success factory correctly populates the PipelineResult object.
    """
    base_path = "/tmp/input"
    final_path = "/tmp/output/transcript"

    # Simulate service results
    trans_res = {
        "counters": {"processed": 10},
        "generated": {"modules": "path/to/modules.txt"}
    }

    result = create_success_result(
        cfg=mock_config_dict,
        base_path=base_path,
        final_output_path=final_path,
        existing_files=[],
        trans_res=trans_res,
        tree_lines=["root", "file"],
        token_count=500
    )

    assert isinstance(result, PipelineResult)
    assert result.ok is True
    assert result.error == ""
    assert result.token_count == 500
    assert result.tree_lines == ["root", "file"]

    # Check flags propagated from config
    assert result.process_modules is True
    assert result.enable_sanitizer is False


def test_create_error_result_handles_defaults(mock_config_dict):
    """
    Verify that the error factory creates a safe result object even
    with minimal input.
    """
    error_msg = "Critical disk error"

    result = create_error_result(
        error=error_msg,
        cfg=mock_config_dict,
        base_path="/tmp/input"
    )

    assert result.ok is False
    assert result.error == error_msg
    assert result.token_count == 0
    assert result.existing_files == []


def test_transcription_error_dto():
    """Verify simple DTO integrity."""
    err = TranscriptionError(rel_path="src/buggy.py", error="SyntaxError")
    assert err.rel_path == "src/buggy.py"
    assert err.error == "SyntaxError"


def test_filenode_dto():
    """Verify FileNode integrity."""
    node = FileNode(path="/abs/path/to/file.py")
    assert node.path == "/abs/path/to/file.py"