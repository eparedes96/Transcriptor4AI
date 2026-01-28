from __future__ import annotations

"""
FileSystem Input/Output Management Service.

Provides atomic, resilient operations for disk manipulation.
Implements 'replace' encoding strategies to prevent crashes with binary files
and ensures directory integrity before write operations.
"""

import logging
import os
import shutil
from typing import List, Optional, Tuple

# Local module logger to avoid circular dependencies
logger = logging.getLogger(__name__)


# ==============================================================================
# DISCOVERY OPERATIONS
# ==============================================================================

def check_existing_output_files(output_dir: str, names: List[str]) -> List[str]:
    """
    Scan a directory for specific filenames and return the full paths of hits.

    Args:
        output_dir: Absolute directory to scan.
        names: Collection of filenames to look for.

    Returns:
        List[str]: List of absolute paths that already exist on disk.
    """
    return [
        os.path.join(output_dir, n)
        for n in names if os.path.exists(os.path.join(output_dir, n))
    ]


def file_exists(path: str) -> bool:
    """Check if a path points to an existing regular file."""
    return os.path.isfile(path)


def directory_exists(path: str) -> bool:
    """Check if a path points to an existing directory."""
    return os.path.isdir(path)


# ==============================================================================
# CONTENT MANIPULATION
# ==============================================================================

def read_file_content(path: str) -> str:
    """
    Read text from disk with high resilience against encoding errors.

    Uses UTF-8 with 'replace' strategy to handle corrupted or binary characters
    without raising UnicodeDecodeError.

    Args:
        path: Absolute path to the source file.

    Returns:
        str: Sanitized text content.
    """
    # 1. READ: Open with error substitution
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_text_file(path: str, content: str) -> None:
    """
    Persist text data to disk, automatically resolving parent directories.

    Args:
        path: Destination absolute path.
        content: String data to write.
    """
    # 1. VALIDATION: Ensure parent path exists before writing
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)

    # 2. PERSISTENCE: Standard UTF-8 write
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ==============================================================================
# STRUCTURAL OPERATIONS
# ==============================================================================

def safe_mkdir(path: str) -> Tuple[bool, Optional[str]]:
    """
    Create a directory hierarchy safely, catching OS-level permission errors.

    Args:
        path: Target directory path.

    Returns:
        Tuple[bool, Optional[str]]: (Success status, Error message if failed).
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True, None
    except OSError as e:
        logger.error(f"IOManager: Directory creation failed at '{path}': {e}")
        return False, str(e)


def delete_file(path: str) -> bool:
    """
    Remove a file from the system if it exists.

    Returns:
        bool: True if file is gone or didn't exist, False on permission error.
    """
    if not os.path.exists(path):
        return True

    try:
        os.remove(path)
        return True
    except OSError as e:
        logger.error(f"IOManager: Deletion failed for '{path}': {e}")
        return False


def move_file(src: str, dst: str) -> bool:
    """
    Transition a file to a new location with automatic overwrite.

    Args:
        src: Source path.
        dst: Destination path.

    Returns:
        bool: True if move succeeded, False otherwise.
    """
    try:
        # 1. CLEANUP: Ensure destination is not blocked
        if os.path.exists(dst):
            os.remove(dst)

        # 2. EXECUTION: High-level move operation
        shutil.move(src, dst)
        return True
    except OSError as e:
        logger.error(f"IOManager: Move failed from '{src}' to '{dst}': {e}")
        return False