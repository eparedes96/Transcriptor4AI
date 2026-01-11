from __future__ import annotations

"""
Pipeline data models and result factories.

This module defines the data structures used to communicate the results
of the transcription pipeline to the consumer interfaces (CLI/GUI).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass(frozen=True)
class PipelineResult:
    """
    Aggregated result of the pipeline execution.

    Attributes:
        ok (bool): True if the pipeline completed successfully.
        error (str): Error message if execution failed.
        base_path (str): The normalized input directory path.
        final_output_path (str): The actual directory where files were saved.
        token_count (int): Estimated number of tokens in the unified file.
        summary (Dict[str, Any]): Detailed statistics and file paths.
    """
    ok: bool
    error: str

    # Normalized Inputs
    base_path: str
    output_base_dir: str
    output_subdir_name: str
    output_prefix: str

    # Flags
    process_modules: bool
    process_tests: bool
    process_resources: bool
    create_individual_files: bool
    create_unified_file: bool

    # Security & Optimization Flags
    enable_sanitizer: bool
    mask_user_paths: bool
    minify_output: bool

    # Output Paths
    final_output_path: str
    existing_files: List[str] = field(default_factory=list)

    # Partial Results
    transcription_res: Dict[str, Any] = field(default_factory=dict)
    tree_lines: List[str] = field(default_factory=list)
    tree_path: str = ""

    # Metrics
    token_count: int = 0

    # Summary
    summary: Dict[str, Any] = field(default_factory=dict)


def create_error_result(
        error: str,
        cfg: Dict[str, Any],
        base_path: str,
        final_output_path: str = "",
        existing_files: Optional[List[str]] = None,
        summary_extra: Optional[Dict[str, Any]] = None
) -> PipelineResult:
    """
    Factory to create a failed PipelineResult.

    Args:
        error: The error message description.
        cfg: The configuration dictionary used during execution.
        base_path: The input directory path.
        final_output_path: The output directory path (if created).
        existing_files: List of pre-existing files that caused conflicts.
        summary_extra: Additional data for the summary dict.
    """
    return PipelineResult(
        ok=False,
        error=error,
        base_path=base_path,
        output_base_dir=cfg.get("output_base_dir", ""),
        output_subdir_name=cfg.get("output_subdir_name", ""),
        output_prefix=cfg.get("output_prefix", ""),
        process_modules=cfg.get("process_modules", False),
        process_tests=cfg.get("process_tests", False),
        process_resources=cfg.get("process_resources", False),
        create_individual_files=cfg.get("create_individual_files", False),
        create_unified_file=cfg.get("create_unified_file", False),
        enable_sanitizer=cfg.get("enable_sanitizer", True),
        mask_user_paths=cfg.get("mask_user_paths", True),
        minify_output=cfg.get("minify_output", False),
        final_output_path=final_output_path,
        existing_files=existing_files or [],
        summary=summary_extra or {},
    )


def create_success_result(
        cfg: Dict[str, Any],
        base_path: str,
        final_output_path: str,
        existing_files: List[str],
        trans_res: Optional[Dict[str, Any]] = None,
        tree_lines: Optional[List[str]] = None,
        tree_path: str = "",
        token_count: int = 0,
        summary_extra: Optional[Dict[str, Any]] = None
) -> PipelineResult:
    """
    Factory to create a successful PipelineResult.

    Args:
        cfg: The configuration dictionary.
        base_path: The input directory.
        final_output_path: The directory where results were saved.
        existing_files: Files that existed before execution.
        trans_res: The result dictionary from the transcription service.
        tree_lines: The generated directory tree as strings.
        tree_path: Path to the saved tree file.
        token_count: The estimated token count.
        summary_extra: Additional summary statistics.
    """
    return PipelineResult(
        ok=True,
        error="",
        base_path=base_path,
        output_base_dir=cfg.get("output_base_dir", ""),
        output_subdir_name=cfg.get("output_subdir_name", ""),
        output_prefix=cfg.get("output_prefix", ""),
        process_modules=cfg.get("process_modules", True),
        process_tests=cfg.get("process_tests", True),
        process_resources=cfg.get("process_resources", True),
        create_individual_files=cfg.get("create_individual_files", True),
        create_unified_file=cfg.get("create_unified_file", True),
        enable_sanitizer=cfg.get("enable_sanitizer", True),
        mask_user_paths=cfg.get("mask_user_paths", True),
        minify_output=cfg.get("minify_output", False),
        final_output_path=final_output_path,
        existing_files=existing_files,
        transcription_res=trans_res or {},
        tree_lines=tree_lines or [],
        tree_path=tree_path,
        token_count=token_count,
        summary=summary_extra or {},
    )