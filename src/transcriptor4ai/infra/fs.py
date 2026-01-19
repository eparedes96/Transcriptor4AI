from __future__ import annotations

"""
FileSystem Infrastructure Layer.

Provides cross-platform path manipulation, directory synchronization, and 
filesystem validation utilities. Acts as an abstraction over the 'os' and 
'platform' modules to ensure uniform behavior across Windows and Unix-like systems.
"""

import os
from typing import List, Optional, Tuple

# -----------------------------------------------------------------------------
# GLOBAL CONSTANTS
# -----------------------------------------------------------------------------

DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"

# -----------------------------------------------------------------------------
# PATH RESOLUTION API
# -----------------------------------------------------------------------------

def get_user_data_dir() -> str:
    """
    Resolve the standard OS-specific directory for persistent application data.

    Automatically creates the hierarchy if it does not exist.
    Standards:
    - Windows: %LOCALAPPDATA%/Transcriptor4AI
    - Linux/Mac: ~/.transcriptor4ai

    Returns:
        str: Absolute path to the application data directory.
    """
    path: str = ""

    # Windows specific resolution
    if os.name == "nt":
        try:
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                path = os.path.join(base, APP_DIR_NAME)
        except Exception:
            pass

    # Posix fallback (Linux/Mac)
    if not path:
        try:
            home = os.path.expanduser("~")
            path = os.path.join(home, UNIX_APP_DIR_NAME)
        except Exception:
            path = os.path.abspath(UNIX_APP_DIR_NAME)

    # Idempotent directory creation
    try:
        os.makedirs(path, exist_ok=True)
    except OSError:
        pass

    return os.path.abspath(path)


def normalize_path(path: Optional[str], fallback: str) -> str:
    """
    Normalize a directory path string into an absolute filesystem path.

    Handles environment variable expansion ($VAR/%VAR%) and user home
    shortcuts (~/). Reverts to fallback if the input is empty or malformed.

    Args:
        path: Raw input path string.
        fallback: Default path to use if resolution fails.

    Returns:
        str: Normalized absolute path.
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
    Calculate the final artifact destination by joining base and subdirectory.

    Args:
        output_base_dir: Parent output directory.
        output_subdir_name: Target subdirectory name.

    Returns:
        str: Resolved absolute output path.
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)

# -----------------------------------------------------------------------------
# FILESYSTEM VALIDATION API
# -----------------------------------------------------------------------------

def get_destination_filenames(
        prefix: str,
        mode: str,
        include_tree: bool,
        include_resources: bool = False
) -> List[str]:
    """
    Predict the generated filenames based on current configuration flags.

    Primarily used for pre-flight collision checks.

    Args:
        prefix: Filename prefix identifier.
        mode: Processing mode selector.
        include_tree: Whether tree generation is active.
        include_resources: Whether resource processing is active.

    Returns:
        List[str]: List of relative filenames expected to be created.
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
    Identify naming collisions in the target output directory.

    Args:
        output_dir: Directory to inspect.
        names: List of filenames to check for existence.

    Returns:
        List[str]: Absolute paths of files that already exist.
    """
    existing: List[str] = []
    for n in names:
        full = os.path.join(output_dir, n)
        if os.path.exists(full):
            existing.append(full)
    return existing


def safe_mkdir(path: str) -> Tuple[bool, Optional[str]]:
    """
    Attempt to recursively create a directory structure safely.

    Args:
        path: Target directory path.

    Returns:
        Tuple[bool, Optional[str]]: (Success flag, Error message if applicable).
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except OSError as e:
        return False, str(e)