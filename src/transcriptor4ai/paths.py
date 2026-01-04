from __future__ import annotations

"""
Path manipulation and filesystem utilities.

Ensures cross-platform compatibility and path normalization.
"""

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
        return os.path.abspath(fallback)


def get_real_output_path(output_base_dir: str, output_subdir_name: str) -> str:
    """
    Construct the final output path: output_base_dir / output_subdir_name
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)


def get_destination_filenames(prefix: str, mode: str, include_tree: bool) -> List[str]:
    """
    Return a list of potential output filenames based on configuration.
    Uses English suffixes for consistency with the v1.1.0 roadmap.
    """
    files: List[str] = []
    if mode in ("all", "tests_only"):
        files.append(f"{prefix}_tests.txt")
    if mode in ("all", "modules_only"):
        files.append(f"{prefix}_modules.txt")
    if include_tree:
        files.append(f"{prefix}_tree.txt")
    return files


def check_existing_output_files(output_dir: str, names: List[str]) -> List[str]:
    """
    Check which files from the list already exist in the output directory.
    Returns a list of full paths of existing files.
    """
    existing: List[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existing.append(full)
    return existing


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