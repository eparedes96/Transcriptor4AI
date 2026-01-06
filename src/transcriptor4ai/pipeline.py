from __future__ import annotations

"""
Core orchestration pipeline.

Coordinates input validation, path preparation, service execution 
(Transcription and Tree generation), and output unification.
"""

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from transcriptor4ai.validate_config import validate_config
from transcriptor4ai.paths import (
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

    # Flags
    process_modules: bool
    process_tests: bool
    create_individual_files: bool
    create_unified_file: bool

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

    Orchestrates the creation of individual parts (Tree, Modules, Tests)
    and optionally assembles them into a unified context file.

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
    # 1) Config & Path Normalization
    # -------------------------------------------------------------------------
    cfg, warnings = validate_config(config, strict=False)

    if warnings:
        for warning in warnings:
            logger.warning(f"Configuration Warning: {warning}")

    fallback_base = os.getcwd()
    base_path = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(base_path) or not os.path.isdir(base_path):
        msg = f"Invalid input directory: {base_path}"
        logger.error(msg)
        return _build_error_result(msg, cfg, base_path)

    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), base_path)
    final_output_path = get_real_output_path(output_base_dir, cfg["output_subdir_name"])
    prefix = cfg["output_prefix"]

    # -------------------------------------------------------------------------
    # 2) Calculate Potential Output Files (For Overwrite Check)
    # -------------------------------------------------------------------------
    files_to_check: List[str] = []

    # Files generated if 'create_individual_files' is True
    if cfg["create_individual_files"]:
        if cfg["process_modules"]:
            files_to_check.append(f"{prefix}_modules.txt")
        if cfg["process_tests"]:
            files_to_check.append(f"{prefix}_tests.txt")
        if cfg["generate_tree"]:
            files_to_check.append(f"{prefix}_tree.txt")

    # Files generated if 'create_unified_file' is True
    if cfg["create_unified_file"]:
        files_to_check.append(f"{prefix}_full_context.txt")

    # Errors file is always a potential output if logging is enabled
    if cfg["save_error_log"]:
        files_to_check.append(f"{prefix}_errors.txt")

    existing_files = check_existing_output_files(final_output_path, files_to_check)

    if existing_files and not overwrite and not dry_run:
        msg = "Existing files detected and overwrite=False. Aborting."
        logger.warning(f"{msg} Files: {existing_files}")
        return _build_error_result(
            msg, cfg, base_path, final_output_path, existing_files,
            summary_extra={"existing_files": list(existing_files)}
        )

    # -------------------------------------------------------------------------
    # 3) Dry Run
    # -------------------------------------------------------------------------
    if dry_run:
        logger.info("Dry run active. No files will be written.")
        return _build_success_result(
            cfg, base_path, final_output_path, existing_files,
            summary_extra={
                "dry_run": True,
                "existing_files": list(existing_files),
                "will_generate": list(files_to_check),
            }
        )

    # -------------------------------------------------------------------------
    # 4) Prepare Output Directories
    # -------------------------------------------------------------------------
    try:
        os.makedirs(final_output_path, exist_ok=True)
    except OSError as e:
        msg = f"Failed to create output directory {final_output_path}: {e}"
        logger.critical(msg)
        return _build_error_result(msg, cfg, base_path, final_output_path)

    # Determine Staging Directory (Real or Temp)
    temp_dir_obj = None
    staging_dir = final_output_path

    if not cfg["create_individual_files"]:
        temp_dir_obj = tempfile.TemporaryDirectory()
        staging_dir = temp_dir_obj.name
        logger.debug(f"Using temporary staging directory: {staging_dir}")

    # Define Paths for Components
    path_modules = os.path.join(staging_dir, f"{prefix}_modules.txt")
    path_tests = os.path.join(staging_dir, f"{prefix}_tests.txt")
    path_tree = tree_output_path if tree_output_path else os.path.join(staging_dir, f"{prefix}_tree.txt")

    path_errors = os.path.join(final_output_path, f"{prefix}_errors.txt")

    path_unified = os.path.join(final_output_path, f"{prefix}_full_context.txt")

    # -------------------------------------------------------------------------
    # 5) Execute Services (Generate Parts)
    # -------------------------------------------------------------------------

    # A. Generate Tree
    tree_lines: List[str] = []
    if cfg["generate_tree"]:
        tree_lines = generate_directory_tree(
            input_path=base_path,
            mode="all",
            extensions=cfg["extensions"],
            include_patterns=cfg["include_patterns"],
            exclude_patterns=cfg["exclude_patterns"],
            show_functions=bool(cfg.get("show_functions")),
            show_classes=bool(cfg.get("show_classes")),
            show_methods=bool(cfg.get("show_methods")),
            print_to_log=bool(cfg.get("print_tree")),
            save_path=path_tree,
        )

    # B. Transcribe Code
    trans_res = transcribe_code(
        input_path=base_path,
        modules_output_path=path_modules,
        tests_output_path=path_tests,
        error_output_path=path_errors,
        process_modules=bool(cfg["process_modules"]),
        process_tests=bool(cfg["process_tests"]),
        extensions=cfg["extensions"],
        include_patterns=cfg["include_patterns"],
        exclude_patterns=cfg["exclude_patterns"],
        save_error_log=bool(cfg["save_error_log"]),
    )

    if not trans_res.get("ok"):
        if temp_dir_obj:
            temp_dir_obj.cleanup()

        err_msg = trans_res.get('error', 'Unknown transcription error')
        return _build_error_result(f"Transcription failure: {err_msg}", cfg, base_path, final_output_path)

    # -------------------------------------------------------------------------
    # 6) Assembly (Unified File)
    # -------------------------------------------------------------------------
    unified_created = False
    if cfg["create_unified_file"]:
        try:
            with open(path_unified, "w", encoding="utf-8") as outfile:
                outfile.write(f"PROJECT CONTEXT: {os.path.basename(base_path)}\n")
                outfile.write("=" * 80 + "\n\n")

                # 1. Append Tree
                if cfg["generate_tree"] and os.path.exists(path_tree):
                    outfile.write("PROJECT STRUCTURE:\n")
                    outfile.write("-" * 50 + "\n")
                    with open(path_tree, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                # 2. Append Modules (Scripts)
                generated_modules = trans_res.get("generated", {}).get("modules")
                if cfg["process_modules"] and generated_modules and os.path.exists(generated_modules):
                    with open(generated_modules, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                # 3. Append Tests
                generated_tests = trans_res.get("generated", {}).get("tests")
                if cfg["process_tests"] and generated_tests and os.path.exists(generated_tests):
                    with open(generated_tests, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

            unified_created = True
            logger.info(f"Unified context file created: {path_unified}")

        except OSError as e:
            logger.error(f"Failed to create unified file: {e}")

    # -------------------------------------------------------------------------
    # 7) Cleanup & Finalize
    # -------------------------------------------------------------------------
    if temp_dir_obj:
        temp_dir_obj.cleanup()
        logger.debug("Temporary staging directory cleaned up.")

    # Update summary for the unified file
    gen_files_map = trans_res.get("generated", {}).copy()
    if unified_created:
        gen_files_map["unified"] = path_unified

    # If individual files were NOT created, remove them from the generated list to avoid confusion
    if not cfg["create_individual_files"]:
        gen_files_map.pop("modules", None)
        gen_files_map.pop("tests", None)

    counters = trans_res.get("counters", {}) or {}
    summary = {
        "final_output_path": final_output_path,
        "processed": int(counters.get("processed", 0)),
        "skipped": int(counters.get("skipped", 0)),
        "errors": int(counters.get("errors", 0)),
        "generated_files": gen_files_map,
        "tree": {
            "generated": bool(cfg.get("generate_tree")),
            "path": path_tree if cfg["create_individual_files"] else None,
            "lines": len(tree_lines),
        },
        "existing_files_before_run": list(existing_files),
        "unified_generated": unified_created
    }

    logger.info("Pipeline completed successfully.")
    return _build_success_result(
        cfg, base_path, final_output_path, existing_files,
        trans_res, tree_lines, path_tree, summary
    )


# -----------------------------------------------------------------------------
# Internal Helpers to reduce boilerplate
# -----------------------------------------------------------------------------
def _build_error_result(
        error: str,
        cfg: Dict[str, Any],
        base_path: str,
        final_output_path: str = "",
        existing_files: List[str] = None,
        summary_extra: Dict[str, Any] = None
) -> PipelineResult:
    return PipelineResult(
        ok=False,
        error=error,
        base_path=base_path,
        output_base_dir=cfg.get("output_base_dir", ""),
        output_subdir_name=cfg.get("output_subdir_name", ""),
        output_prefix=cfg.get("output_prefix", ""),
        process_modules=cfg.get("process_modules", False),
        process_tests=cfg.get("process_tests", False),
        create_individual_files=cfg.get("create_individual_files", False),
        create_unified_file=cfg.get("create_unified_file", False),
        final_output_path=final_output_path,
        existing_files=existing_files or [],
        transcription_res={},
        tree_lines=[],
        tree_path="",
        summary=summary_extra or {},
    )


def _build_success_result(
        cfg: Dict[str, Any],
        base_path: str,
        final_output_path: str,
        existing_files: List[str],
        trans_res: Dict[str, Any] = None,
        tree_lines: List[str] = None,
        tree_path: str = "",
        summary_extra: Dict[str, Any] = None
) -> PipelineResult:
    return PipelineResult(
        ok=True,
        error="",
        base_path=base_path,
        output_base_dir=cfg.get("output_base_dir", ""),
        output_subdir_name=cfg.get("output_subdir_name", ""),
        output_prefix=cfg.get("output_prefix", ""),
        process_modules=cfg.get("process_modules", True),
        process_tests=cfg.get("process_tests", True),
        create_individual_files=cfg.get("create_individual_files", True),
        create_unified_file=cfg.get("create_unified_file", True),
        final_output_path=final_output_path,
        existing_files=existing_files,
        transcription_res=trans_res or {},
        tree_lines=tree_lines or [],
        tree_path=tree_path,
        summary=summary_extra or {},
    )