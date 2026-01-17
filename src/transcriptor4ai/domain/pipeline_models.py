from __future__ import annotations

"""
Pipeline Domain Data Models.

Defines the core data structures and factory functions used to communicate 
execution results between the pipeline engine and interface layers (CLI/GUI).
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# -----------------------------------------------------------------------------
# CORE DATA MODELS
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class PipelineResult:
    """
    Unified result object of a complete pipeline execution.

    Encapsulates execution status, normalized configuration, metrics,
    and paths to generated artifacts.

    Attributes:
        ok: Flag indicating success or failure.
        error: Descriptive message in case of failure.
        base_path: Normalized root directory processed.
        output_base_dir: Root directory for output artifacts.
        output_subdir_name: Subdirectory where results are saved.
        output_prefix: User-defined prefix for generated files.
        process_modules: Whether source logic was targeted.
        process_tests: Whether test files were targeted.
        process_resources: Whether project resources were targeted.
        create_individual_files: Flag for categorized output files.
        create_unified_file: Flag for single aggregated context file.
        enable_sanitizer: Flag for PII/Secret redaction.
        mask_user_paths: Flag for environment anonymization.
        minify_output: Flag for code comment removal.
        final_output_path: Absolute directory containing artifacts.
        existing_files: List of paths that caused naming collisions.
        transcription_res: Metadata from categorized workers.
        tree_lines: Text lines representing the directory tree.
        tree_path: Absolute path to the persisted tree file.
        token_count: Estimated token density of the unified context.
        summary: Technical execution summary and statistics.
    """
    ok: bool
    error: str

    base_path: str
    output_base_dir: str
    output_subdir_name: str
    output_prefix: str

    process_modules: bool
    process_tests: bool
    process_resources: bool
    create_individual_files: bool
    create_unified_file: bool

    enable_sanitizer: bool
    mask_user_paths: bool
    minify_output: bool

    final_output_path: str
    existing_files: List[str] = field(default_factory=list)

    transcription_res: Dict[str, Any] = field(default_factory=dict)
    tree_lines: List[str] = field(default_factory=list)
    tree_path: str = ""

    token_count: int = 0

    summary: Dict[str, Any] = field(default_factory=dict)

# -----------------------------------------------------------------------------
# FACTORY FUNCTIONS
# -----------------------------------------------------------------------------

def create_error_result(
        error: str,
        cfg: Dict[str, Any],
        base_path: str,
        final_output_path: str = "",
        existing_files: Optional[List[str]] = None,
        summary_extra: Optional[Dict[str, Any]] = None
) -> PipelineResult:
    """
    Create a failed pipeline result instance.

    Args:
        error: Detailed error description.
        cfg: The configuration used during the failed run.
        base_path: The target input directory.
        final_output_path: Calculated output directory.
        existing_files: Files that caused collision aborts.
        summary_extra: Additional metadata for the summary payload.

    Returns:
        PipelineResult: An immutable error result object.
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
    Create a successful pipeline result instance.

    Args:
        cfg: Final configuration used during execution.
        base_path: Normalized input directory.
        final_output_path: Absolute artifact directory.
        existing_files: Collision artifacts (if any were permitted).
        trans_res: Metadata from worker execution.
        tree_lines: Generated ASCII tree content.
        tree_path: Path to the structural tree file.
        token_count: Final token count metrics.
        summary_extra: Final execution metrics.

    Returns:
        PipelineResult: An immutable success result object.
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