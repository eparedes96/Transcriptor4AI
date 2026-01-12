from __future__ import annotations

"""
FileSystem Infrastructure Layer.

Provides cross-platform path manipulation, directory creation, and file checking utilities.
Acts as an abstraction layer over the 'os' module to ensure consistent behavior across OSs.
"""

import os
import platform
from typing import List, Optional, Tuple

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"


# -----------------------------------------------------------------------------
# Path Helpers
# -----------------------------------------------------------------------------
def get_user_data_dir() -> str:
    """
    Get the standard OS-specific user data directory for the application.
    Automatically creates the directory if it does not exist.

    Path Standards:
    - Windows: %LOCALAPPDATA%/Transcriptor4AI
    - Linux/Mac: ~/.transcriptor4ai

    Returns:
        str: Absolute path to the user data directory.
    """
    path: str = ""

    # Windows Logic
    if os.name == "nt":
        try:
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                path = os.path.join(base, APP_DIR_NAME)
        except Exception:
            pass

    # Fallback or Non-Windows (Linux/Mac)
    if not path:
        try:
            home = os.path.expanduser("~")
            path = os.path.join(home, UNIX_APP_DIR_NAME)
        except Exception:
            path = os.path.abspath(UNIX_APP_DIR_NAME)

    # Ensure directory exists
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass

    return os.path.abspath(path)


def normalize_path(path: Optional[str], fallback: str) -> str:
    """
    Normalize a directory path string.

    - Handles None/Empty inputs by returning the fallback.
    - Expands user (~/) and environment variables ($VAR/%VAR%).
    - Returns an absolute path.

    Args:
        path: The input path string (can be None).
        fallback: The default path to use if input is invalid.

    Returns:
        str: The normalized, absolute path.
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
    Construct the final output path combining base and subdirectory.
    Defaults to 'transcript' if subdir is missing.

    Args:
        output_base_dir: The parent directory.
        output_subdir_name: The name of the subdirectory.

    Returns:
        str: The joined path.
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)


def get_destination_filenames(
        prefix: str,
        mode: str,
        include_tree: bool,
        include_resources: bool = False
) -> List[str]:
    """
    Generate a list of potential output filenames based on configuration flags.
    Used for checking overwrite conflicts.

    Args:
        prefix: The filename prefix (e.g., 'project_v1').
        mode: Processing mode ('all', 'modules_only', 'tests_only').
        include_tree: Whether tree file is expected.
        include_resources: Whether resource file is expected.

    Returns:
        List[str]: List of expected filenames.
    """
    files: List[str] = []

    if mode in ("all", "tests_only"):
        files.append(f"{prefix}_tests.txt")

    if mode in ("all", "modules_only"):
        files.append(f"{prefix}_modules.txt")

    if include_resources:
        files.append(f"{prefix}_resources.txt")

    if include_tree:
        files.append(f"{prefix}_tree.txt")

    return files


def check_existing_output_files(output_dir: str, names: List[str]) -> List[str]:
    """
    Check which files from a list already exist in the target directory.

    Args:
        output_dir: The directory to check within.
        names: List of filenames to check.

    Returns:
        List[str]: A list of full paths for files that already exist.
    """
    existing: List[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existing.append(full)
    return existing


def safe_mkdir(path: str) -> Tuple[bool, Optional[str]]:
    """
    Attempt to create a directory structure recursively (idempotent).

    Args:
        path: The directory path to create.

    Returns:
        Tuple[bool, Optional[str]]: (Success, Error Message).
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except OSError as e:
        return False, str(e)