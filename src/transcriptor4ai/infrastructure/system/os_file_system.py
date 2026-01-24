from __future__ import annotations

"""
FileSystem Infrastructure Adapter.

Concrete implementation of filesystem operations. Acts as an abstraction layer
over the 'os' and 'platform' modules to ensure uniform behavior across Windows
and Unix-like systems.
"""

import logging
import os
import platform
import subprocess
from typing import List, Optional, Tuple

from transcriptor4ai.shared import constants as const

logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTS
# ==============================================================================
DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"


# ==============================================================================
# FILESYSTEM ADAPTER
# ==============================================================================
class FileSystemAdapter:
    """
    Adapter for OS-level file and directory operations.
    """

    def get_user_data_dir(self) -> str:
        """
        Resolve the standard OS-specific directory for persistent application data.

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
        except OSError as e:
            logger.error(f"FileSystem: Failed to create data dir at {path}: {e}")

        return os.path.abspath(path)

    def get_pricing_cache_path(self) -> str:
        """
        Resolve the absolute path for the local pricing cache file.

        Returns:
            str: Absolute path to the pricing cache JSON file.
        """
        base_dir = self.get_user_data_dir()
        return os.path.join(base_dir, const.LOCAL_PRICING_FILENAME)

    def normalize_path(self, path: Optional[str], fallback: str) -> str:
        """
        Normalize a directory path string into an absolute filesystem path.

        Handles environment variable expansion ($VAR) and user home (~).

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

    def get_real_output_path(self, output_base_dir: str, output_subdir_name: str) -> str:
        """
        Calculate the final artifact destination.

        Args:
            output_base_dir: Parent output directory.
            output_subdir_name: Target subdirectory name.

        Returns:
            str: Resolved absolute output path.
        """
        sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
        return os.path.join(output_base_dir, sub)

    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
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

    def safe_mkdir(self, path: str) -> Tuple[bool, Optional[str]]:
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

    def open_file_explorer(self, path: str) -> None:
        """
        Execute the host operating system's native file explorer.

        Supports Windows (explorer.exe), macOS (open), and Linux (xdg-open).

        Args:
            path: Absolute directory path to open.

        Raises:
            FileNotFoundError: If the path does not exist.
            OSError: If the system command fails.
        """
        if not os.path.exists(path):
            logger.warning(f"FileSystem: Attempted to open non-existent path: {path}")
            raise FileNotFoundError(f"Path does not exist: {path}")

        try:
            sys_name = platform.system()
            if sys_name == "Windows":
                os.startfile(path)
            elif sys_name == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            logger.error(f"FileSystem: Failed to invoke file explorer: {e}")
            raise OSError(f"Could not open file explorer: {e}") from e