from __future__ import annotations

"""
FileSystem Path Resolution Service.

Provides centralized logic for OS-specific path discovery, normalization,
and artifact naming conventions. This module is infrastructure-pure and
does not perform direct disk I/O.
"""

import logging
import os
from typing import Any, Dict, List, Optional

from transcriptor4ai.shared import constants as const

# Internal module logger
logger = logging.getLogger(__name__)

# ==============================================================================
# MODULE CONSTANTS
# ==============================================================================

DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"


# ==============================================================================
# PUBLIC PATH API
# ==============================================================================

def get_expected_filenames(cfg: Dict[str, Any], prefix: str) -> List[str]:
    """
    Determine the standard filenames that the pipeline expects to generate.

    Args:
        cfg: Active session configuration dictionary.
        prefix: User-defined output prefix.

    Returns:
        List[str]: Collection of expected filenames based on active flags.
    """
    files: List[str] = []

    # 1. EVALUATION: Check individual file flags
    if cfg.get("create_individual_files"):
        if cfg.get("process_modules"):
            files.append(f"{prefix}_modules.txt")
        if cfg.get("process_tests"):
            files.append(f"{prefix}_tests.txt")
        if cfg.get("process_resources"):
            files.append(f"{prefix}_resources.txt")
        if cfg.get("generate_tree"):
            files.append(f"{prefix}_tree.txt")

    # 2. EVALUATION: Check aggregate and log flags
    if cfg.get("create_unified_file"):
        files.append(f"{prefix}_full_context.txt")

    if cfg.get("save_error_log"):
        files.append(f"{prefix}_errors.txt")

    return files


def get_user_data_dir() -> str:
    """
    Resolve the OS-specific directory for persistent application data.

    Returns:
        str: Absolute path to the data directory, expanded and normalized.
    """
    path: str = ""

    # 1. PLATFORM DETECTION: Windows branch
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if base:
            path = os.path.join(base, APP_DIR_NAME)

    # 2. PLATFORM DETECTION: Unix/Darwin branch or fallback
    if not path:
        home = os.path.expanduser("~")
        path = os.path.join(home, UNIX_APP_DIR_NAME)

    try:
        os.makedirs(path, exist_ok=True)
    except FileExistsError:
        # Final safety check: if it's already a directory, we can proceed
        if not os.path.isdir(path):
            raise

    return os.path.abspath(path)


def get_pricing_cache_path() -> str:
    """
    Resolve the absolute path for the dynamic model pricing metadata cache.

    Returns:
        str: Path to the pricing JSON file within user data.
    """
    return os.path.join(get_user_data_dir(), const.LOCAL_PRICING_FILENAME)


def normalize_path(path: Optional[str], fallback: str) -> str:
    """
    Expand system variables and user shortcuts in a filesystem path.

    Args:
        path: Raw path string from input.
        fallback: Directory to use if the input path is null or empty.

    Returns:
        str: Fully qualified absolute path.
    """
    p = (path or "").strip() or fallback

    try:
        # Resolves both environment vars ($VAR) and user home (~)
        p = os.path.expandvars(os.path.expanduser(p))
        return os.path.abspath(p)
    except Exception as e:
        logger.debug(f"PathResolver: Normalization failed for '{p}': {e}")
        return os.path.abspath(fallback)


def get_real_output_path(output_base_dir: str, output_subdir_name: str) -> str:
    """
    Construct the final destination path for transcription artifacts.

    Args:
        output_base_dir: The parent directory.
        output_subdir_name: The specific folder name for this session.

    Returns:
        str: Joined absolute path.
    """
    sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
    return os.path.join(output_base_dir, sub)