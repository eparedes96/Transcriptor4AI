from __future__ import annotations

import os
from typing import List, Optional, Tuple

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
DEFAULT_OUTPUT_SUBDIR = "transcript"


# -----------------------------------------------------------------------------
# Path Helpers
# -----------------------------------------------------------------------------
def normalize_path(path: Optional[str], fallback: str) -> str:
    """
    Normalize a directory path.
    - Handles None/Empty by using fallback.
    - Expands user (~/) and environment variables.
    - Returns an absolute path.
    """
    p = (path or "").strip()
    if not p:
        p = fallback
    try:
        p = os.path.expandvars(os.path.expanduser(p))
        return os.path.abspath(p)
    except Exception:
        # In case of rare path errors, return absolute fallback
        return os.path.abspath(fallback)


def get_real_output_path(output_base_dir: str, output_subdir_name: str) -> str:
    """
    Construct the final output path: output_base_dir / output_subdir_name
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)


def get_destination_filenames(prefix: str, modo: str, incluir_arbol: bool) -> List[str]:
    """
    Return a list of potential output filenames based on configuration.
    Does not return full paths, only filenames.
    """
    files: List[str] = []
    if modo in ("todo", "solo_tests"):
        files.append(f"{prefix}_tests.txt")
    if modo in ("todo", "solo_modulos"):
        files.append(f"{prefix}_modulos.txt")
    if incluir_arbol:
        files.append(f"{prefix}_arbol.txt")
    return files


def check_existing_output_files(output_dir: str, names: List[str]) -> List[str]:
    """
    Check which files from the list already exist in the output directory.
    Returns a list of full paths of existing files.
    """
    existentes: List[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existentes.append(full)
    return existentes


def _safe_mkdir(path: str) -> Tuple[bool, Optional[str]]:
    """
    Attempt to create a directory (idempotent).
    Returns (Success, ErrorMessage).
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except OSError as e:
        return False, str(e)