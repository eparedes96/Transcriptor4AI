from __future__ import annotations

"""
Core orchestration pipeline.

Coordinates input validation, path preparation, and service execution 
(Transcription and Tree generation).
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.paths import (
    get_destination_filenames,
    check_existing_output_files,
    normalize_path,
    get_real_output_path,
)
from transcriptor4ai.transcription.service import transcribe_code
from transcriptor4ai.tree.service import generate_directory_tree

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Results Models
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class PipelineResult:
    """Aggregated result of the pipeline execution."""
    ok: bool
    error: str

    # Normalized Inputs
    base_path: str
    output_base_dir: str
    output_subdir_name: str
    output_prefix: str
    processing_mode: str

    # Output Paths
    final_output_path: str
    existing_files: List[str]

    # Partial Results
    transcription_res: Dict[str, Any]
    tree_lines: List[str]
    tree_path: str

    # Summary
    summary: Dict[str, Any]


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------
def run_pipeline(
        config: Optional[Dict[str, Any]],
        *,
        overwrite: bool = False,
        dry_run: bool = False,
        tree_output_path: Optional[str] = None,
) -> PipelineResult:
    """
    Execute the full transcription pipeline.

    Args:
        config: Configuration dictionary (will be validated).
        overwrite: If False, aborts if output files already exist.
        dry_run: If True, calculates paths but does not write files.
        tree_output_path: Optional override for tree output file.

    Returns:
        PipelineResult object.
    """
    logger.info("Pipeline execution started.")

    # -------------------------------------------------------------------------
    # 1) Config & Path Normalization (Gatekeeper)
    # -------------------------------------------------------------------------
    # Redundancy removed: pipeline now trusts validate_config exclusively.
    cfg, warnings = validate_config(config, strict=False)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Warning: {warning}")

    fallback_base = os.getcwd()
    base_path = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid input directory: {base_path}"
        logger.error(msg)
        return PipelineResult(
            ok=False,
            error=msg,
            base_path=base_path,
            output_base_dir="",
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            processing_mode=cfg["processing_mode"],
            final_output_path="",
            existing_files=[],
            transcription_res={},
            tree_lines=[],
            tree_path="",
            summary={},
        )

    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), base_path)
    final_output_path = get_real_output_path(output_base_dir, cfg["output_subdir_name"])

    # -------------------------------------------------------------------------
    # 2) Overwrite Check
    # -------------------------------------------------------------------------
    target_names = get_destination_filenames(
        cfg["output_prefix"],
        cfg["processing_mode"],
        bool(cfg.get("generate_tree"))
    )
    existing_files = check_existing_output_files(final_output_path, target_names)

    if existing_files and not overwrite and not dry_run:
        msg = "Existing files detected and overwrite=False. Aborting."
        logger.warning(f"{msg} Files: {existing_files}")
        return PipelineResult(
            ok=False,
            error=msg,
            base_path=base_path,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            processing_mode=cfg["processing_mode"],
            final_output_path=final_output_path,
            existing_files=existing_files,
            transcription_res={},
            tree_lines=[],
            tree_path="",
            summary={
                "processed": 0,
                "skipped": 0,
                "errors": 0,
                "existing_files": list(existing_files),
            },
        )

    if dry_run:
        logger.info("Dry run active. No files will be written.")
        return PipelineResult(
            ok=True,
            error="",
            base_path=base_path,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            processing_mode=cfg["processing_mode"],
            final_output_path=final_output_path,
            existing_files=existing_files,
            transcription_res={},
            tree_lines=[],
            tree_path=os.path.join(final_output_path, f"{cfg['output_prefix']}_tree.txt") if cfg.get(
                "generate_tree") else "",
            summary={
                "dry_run": True,
                "existing_files": list(existing_files),
                "will_generate": list(target_names),
            },
        )

    # -------------------------------------------------------------------------
    # 3) Ensure Output Directory
    # -------------------------------------------------------------------------
    try:
        os.makedirs(final_output_path, exist_ok=True)
    except OSError as e:
        msg = f"Failed to create output directory {final_output_path}: {e}"
        logger.critical(msg)
        return PipelineResult(
            ok=False,
            error=msg,
            base_path=base_path,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            processing_mode=cfg["processing_mode"],
            final_output_path=final_output_path,
            existing_files=existing_files,
            transcription_res={},
            tree_lines=[],
            tree_path="",
            summary={},
        )

    # -------------------------------------------------------------------------
    # 4) Execute Transcription Service
    # -------------------------------------------------------------------------
    trans_res = transcribe_code(
        input_path=base_path,
        mode=cfg["processing_mode"],
        extensions=cfg["extensions"],
        include_patterns=cfg["include_patterns"],
        exclude_patterns=cfg["exclude_patterns"],
        output_prefix=cfg["output_prefix"],
        output_folder=final_output_path,
        save_error_log=bool(cfg.get("save_error_log")),
    )

    if not trans_res.get("ok"):
        err_msg = trans_res.get('error', 'Unknown transcription error')
        logger.error(f"Transcription failed: {err_msg}")
        return PipelineResult(
            ok=False,
            error=f"Transcription failure: {err_msg}",
            base_path=base_path,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            processing_mode=cfg["processing_mode"],
            final_output_path=final_output_path,
            existing_files=existing_files,
            transcription_res=trans_res,
            tree_lines=[],
            tree_path="",
            summary={},
        )

    # -------------------------------------------------------------------------
    # 5) Execute Tree Service
    # -------------------------------------------------------------------------
    tree_lines: List[str] = []
    tree_path = ""
    if cfg.get("generate_tree"):
        tree_path = tree_output_path if tree_output_path else os.path.join(final_output_path,
                                                                           f"{cfg['output_prefix']}_tree.txt")

        tree_lines = generate_directory_tree(
            input_path=base_path,
            mode=cfg["processing_mode"],
            extensions=cfg["extensions"],
            include_patterns=cfg["include_patterns"],
            exclude_patterns=cfg["exclude_patterns"],
            show_functions=bool(cfg.get("show_functions")),
            show_classes=bool(cfg.get("show_classes")),
            show_methods=bool(cfg.get("show_methods")),
            print_to_log=bool(cfg.get("print_tree")),
            save_path=tree_path,
        )

    # -------------------------------------------------------------------------
    # 6) Final Summary
    # -------------------------------------------------------------------------
    counters = trans_res.get("counters", {}) or {}
    summary = {
        "final_output_path": final_output_path,
        "processed": int(counters.get("processed", 0)),
        "skipped": int(counters.get("skipped", 0)),
        "errors": int(counters.get("errors", 0)),
        "generated_files": (trans_res.get("generated", {}) or {}),
        "tree": {
            "generated": bool(cfg.get("generate_tree")),
            "path": tree_path,
            "lines": len(tree_lines),
        },
        "existing_files_before_run": list(existing_files),
    }

    logger.info("Pipeline completed successfully.")
    return PipelineResult(
        ok=True,
        error="",
        base_path=base_path,
        output_base_dir=output_base_dir,
        output_subdir_name=cfg["output_subdir_name"],
        output_prefix=cfg["output_prefix"],
        processing_mode=cfg["processing_mode"],
        final_output_path=final_output_path,
        existing_files=existing_files,
        transcription_res=trans_res,
        tree_lines=tree_lines,
        tree_path=tree_path,
        summary=summary,
    )