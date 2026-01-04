from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from transcriptor4ai.config import (
    DEFAULT_OUTPUT_PREFIX,
    get_default_config,
)
from transcriptor4ai.filtering import (
    default_extensiones,
    default_exclude_patterns,
    default_include_patterns,
)
from transcriptor4ai.paths import (
    DEFAULT_OUTPUT_SUBDIR,
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
    ruta_base: str
    output_base_dir: str
    output_subdir_name: str
    output_prefix: str
    modo: str

    # Output Paths
    salida_real: str
    existentes: List[str]

    # Partial Results
    res_transcripcion: Dict[str, Any]
    res_arbol_lines: List[str]
    ruta_arbol: str

    # Summary
    resumen: Dict[str, Any]


# -----------------------------------------------------------------------------
# Normalization Helpers (Internal)
# -----------------------------------------------------------------------------
def _ensure_list(value: Any, fallback: List[str]) -> List[str]:
    if value is None:
        return list(fallback)
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        items = [x.strip() for x in value.split(",") if x.strip()]
        return items if items else list(fallback)
    return list(fallback)


def _ensure_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return fallback
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "si", "sí"):
            return True
        if v in ("0", "false", "no", "n"):
            return False
    return fallback


def _normalize_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Internal normalization to ensure the pipeline is safe even if called
    without external validation.
    """
    defaults = get_default_config()
    cfg: Dict[str, Any] = dict(defaults)
    if isinstance(config, dict):
        cfg.update(config)

    # Mode
    modo = (cfg.get("processing_mode") or "todo").strip()
    if modo not in ("todo", "solo_modulos", "solo_tests"):
        modo = "todo"
    cfg["processing_mode"] = modo

    # Lists
    cfg["extensiones"] = _ensure_list(cfg.get("extensiones"), default_extensiones())
    cfg["include_patterns"] = _ensure_list(cfg.get("include_patterns"), default_include_patterns())
    cfg["exclude_patterns"] = _ensure_list(cfg.get("exclude_patterns"), default_exclude_patterns())

    # Bools
    cfg["generate_tree"] = _ensure_bool(cfg.get("generate_tree"), False)
    cfg["print_tree"] = _ensure_bool(cfg.get("print_tree"), True)
    cfg["save_error_log"] = _ensure_bool(cfg.get("save_error_log"), True)
    cfg["show_functions"] = _ensure_bool(cfg.get("show_functions"), False)
    cfg["show_classes"] = _ensure_bool(cfg.get("show_classes"), False)
    cfg["show_methods"] = _ensure_bool(cfg.get("show_methods"), False)

    # Strings
    cfg["output_subdir_name"] = (cfg.get("output_subdir_name") or DEFAULT_OUTPUT_SUBDIR).strip() or DEFAULT_OUTPUT_SUBDIR
    cfg["output_prefix"] = (cfg.get("output_prefix") or DEFAULT_OUTPUT_PREFIX).strip() or DEFAULT_OUTPUT_PREFIX

    return cfg


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
        config: Configuration dictionary (will be normalized).
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
    cfg = _normalize_config(config)

    fallback_base = os.getcwd()
    ruta_base = normalize_path(cfg.get("input_path", ""), fallback_base)

    if not os.path.exists(ruta_base) or not os.path.isdir(ruta_base):
        msg = f"Invalid input directory: {ruta_base}"
        logger.error(msg)
        return PipelineResult(
            ok=False,
            error=msg,
            ruta_base=ruta_base,
            output_base_dir="",
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["processing_mode"],
            salida_real="",
            existentes=[],
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    output_base_dir = normalize_path(cfg.get("output_base_dir", ""), ruta_base)
    salida_real = get_real_output_path(output_base_dir, cfg["output_subdir_name"])

    # -------------------------------------------------------------------------
    # 2) Overwrite Check
    # -------------------------------------------------------------------------
    nombres = get_destination_filenames(cfg["output_prefix"], cfg["processing_mode"], bool(cfg.get("generate_tree")))
    existentes = check_existing_output_files(salida_real, nombres)

    if existentes and not overwrite and not dry_run:
        msg = "Existing files detected and overwrite=False. Aborting."
        logger.warning(f"{msg} Files: {existentes}")
        return PipelineResult(
            ok=False,
            error=msg,
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["processing_mode"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={
                "procesados": 0,
                "omitidos": 0,
                "errores": 0,
                "existing_files": list(existentes),
            },
        )

    if dry_run:
        logger.info("Dry run active. No files will be written.")
        return PipelineResult(
            ok=True,
            error="",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["processing_mode"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol=os.path.join(salida_real, f"{cfg['output_prefix']}_arbol.txt") if cfg.get("generate_tree") else "",
            resumen={
                "dry_run": True,
                "existing_files": list(existentes),
                "will_generate": list(nombres),
            },
        )

    # -------------------------------------------------------------------------
    # 3) Ensure Output Directory
    # -------------------------------------------------------------------------
    try:
        os.makedirs(salida_real, exist_ok=True)
    except OSError as e:
        msg = f"Failed to create output directory {salida_real}: {e}"
        logger.critical(msg)
        return PipelineResult(
            ok=False,
            error=msg,
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["processing_mode"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion={},
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    # -------------------------------------------------------------------------
    # 4) Execute Transcription Service
    # -------------------------------------------------------------------------
    res_trans = transcribe_code(
        ruta_base=ruta_base,
        modo=cfg["processing_mode"],
        extensiones=cfg["extensiones"],
        include_patterns=cfg["include_patterns"],
        exclude_patterns=cfg["exclude_patterns"],
        archivo_salida=cfg["output_prefix"],
        output_folder=salida_real,
        save_error_log=bool(cfg.get("save_error_log")),
    )

    if not res_trans.get("ok"):
        err_msg = res_trans.get('error', 'Unknown transcription error')
        logger.error(f"Transcription failed: {err_msg}")
        return PipelineResult(
            ok=False,
            error=f"Transcription failure: {err_msg}",
            ruta_base=ruta_base,
            output_base_dir=output_base_dir,
            output_subdir_name=cfg["output_subdir_name"],
            output_prefix=cfg["output_prefix"],
            modo=cfg["processing_mode"],
            salida_real=salida_real,
            existentes=existentes,
            res_transcripcion=res_trans,
            res_arbol_lines=[],
            ruta_arbol="",
            resumen={},
        )

    # -------------------------------------------------------------------------
    # 5) Execute Tree Service
    # -------------------------------------------------------------------------
    arbol_lines: List[str] = []
    ruta_arbol = ""
    if cfg.get("generate_tree"):
        # Prioritize override path (CLI flag), else default
        ruta_arbol = tree_output_path if tree_output_path else os.path.join(salida_real, f"{cfg['output_prefix']}_arbol.txt")

        arbol_lines = generate_directory_tree(
            ruta_base=ruta_base,
            modo=cfg["processing_mode"],
            extensiones=cfg["extensiones"],
            include_patterns=cfg["include_patterns"],
            exclude_patterns=cfg["exclude_patterns"],
            show_functions=bool(cfg.get("show_functions")),
            show_classes=bool(cfg.get("show_classes")),
            show_methods=bool(cfg.get("show_methods")),
            imprimir=bool(cfg.get("print_tree")),
            guardar_archivo=ruta_arbol,
        )

    # -------------------------------------------------------------------------
    # 6) Final Summary
    # -------------------------------------------------------------------------
    cont = res_trans.get("contadores", {}) or {}
    resumen = {
        "salida_real": salida_real,
        "procesados": int(cont.get("procesados", 0)),
        "omitidos": int(cont.get("omitidos", 0)),
        "errores": int(cont.get("errores", 0)),
        "generados": (res_trans.get("generados", {}) or {}),
        "arbol": {
            "generado": bool(cfg.get("generate_tree")),
            "ruta": ruta_arbol,
            "lineas": len(arbol_lines),
        },
        "existing_files_before_run": list(existentes),
    }

    logger.info("Pipeline completed successfully.")
    return PipelineResult(
        ok=True,
        error="",
        ruta_base=ruta_base,
        output_base_dir=output_base_dir,
        output_subdir_name=cfg["output_subdir_name"],
        output_prefix=cfg["output_prefix"],
        modo=cfg["processing_mode"],
        salida_real=salida_real,
        existentes=existentes,
        res_transcripcion=res_trans,
        res_arbol_lines=arbol_lines,
        ruta_arbol=ruta_arbol,
        resumen=resumen,
    )