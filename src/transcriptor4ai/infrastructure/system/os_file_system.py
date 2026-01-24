from __future__ import annotations

"""
FileSystem Infrastructure Adapter.

Concrete implementation of filesystem operations. Acts as an abstraction layer
over the 'os', 'platform', and 'zipfile' modules to ensure uniform behavior 
across different operating systems and handle complex I/O tasks like 
binary extraction.
"""

import logging
import os
import platform
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple

from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.shared import constants as const

logger = logging.getLogger(__name__)

# ==============================================================================
# CONSTANTS
# ==============================================================================
DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"


# ==============================================================================
# FILESYSTEM ADAPTER IMPLEMENTATION
# ==============================================================================

class FileSystemAdapter(IFileSystem):
    """
    Adapter for OS-level file, directory, and archive operations.
    """

    # --------------------------------------------------------------------------
    # DIRECTORY RESOLUTION
    # --------------------------------------------------------------------------

    def get_user_data_dir(self) -> str:
        """
        Resolve the standard OS-specific directory for persistent application data.

        Returns:
            str: Absolute path to the application data directory.
        """
        path: str = ""

        if os.name == "nt":
            try:
                base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
                if base:
                    path = os.path.join(base, APP_DIR_NAME)
            except Exception:
                pass

        if not path:
            try:
                home = os.path.expanduser("~")
                path = os.path.join(home, UNIX_APP_DIR_NAME)
            except Exception:
                path = os.path.abspath(UNIX_APP_DIR_NAME)

        try:
            os.makedirs(path, exist_ok=True)
        except OSError as e:
            logger.error(f"FileSystem: Failed to create data dir at {path}: {e}")

        return os.path.abspath(path)

    def get_pricing_cache_path(self) -> str:
        """Resolve the path for the pricing cache JSON file."""
        base_dir = self.get_user_data_dir()
        return os.path.join(base_dir, const.LOCAL_PRICING_FILENAME)

    # --------------------------------------------------------------------------
    # PATH MANIPULATION
    # --------------------------------------------------------------------------

    def normalize_path(self, path: Optional[str], fallback: str) -> str:
        """
        Normalize a path string handles env vars and user home shortcuts.
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
        """Calculate final destination joining base and subfolder."""
        sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
        return os.path.join(output_base_dir, sub)

    # --------------------------------------------------------------------------
    # FILESYSTEM OPERATIONS
    # --------------------------------------------------------------------------

    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
        """Identify naming collisions in the target directory."""
        existing: List[str] = []
        for n in names:
            full = os.path.join(output_dir, n)
            if os.path.exists(full):
                existing.append(full)
        return existing

    def safe_mkdir(self, path: str) -> Tuple[bool, Optional[str]]:
        """Attempt to recursively create a directory structure safely."""
        try:
            os.makedirs(path, exist_ok=True)
            return True, None
        except OSError as e:
            return False, str(e)

    def delete_file(self, path: str) -> bool:
        """
        Safely remove a file from the filesystem.

        Returns:
            bool: True if deleted or already absent, False on permission errors.
        """
        if not os.path.exists(path):
            return True
        try:
            os.remove(path)
            return True
        except OSError as e:
            logger.error(f"FileSystem: Failed to delete '{path}': {e}")
            return False

    # --------------------------------------------------------------------------
    # ARCHIVE MANAGEMENT
    # --------------------------------------------------------------------------

    def unpack_executable_from_zip(self, zip_path: str, extract_to: str) -> Optional[str]:
        """
        Extract the main application binary from a compressed update package.

        Args:
            zip_path: Path to the .zip archive.
            extract_to: Directory where the binary should be placed.

        Returns:
            Optional[str]: Path to the extracted executable, or None on failure.
        """
        # 1. VALIDATION: Check archive integrity
        if not zipfile.is_zipfile(zip_path):
            logger.error(f"FileSystem: '{zip_path}' is not a valid ZIP archive.")
            return None

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 2. DISCOVERY: Filter for executable files
                exe_files = [f for f in zf.namelist() if f.lower().endswith(".exe")]

                if not exe_files:
                    logger.error("FileSystem: No executable found in update package.")
                    return None

                # 3. SELECTION: Apply heuristic to find the primary app binary
                target_name = next(
                    (f for f in exe_files if "transcriptor" in f.lower()),
                    exe_files[0]
                )

                # 4. EXTRACTION: Atomically write to target directory
                zf.extract(target_name, extract_to)
                extracted_path = os.path.join(extract_to, target_name)

                logger.debug(f"FileSystem: Binary extracted to {extracted_path}")
                return extracted_path

        except (zipfile.BadZipFile, OSError) as e:
            logger.error(f"FileSystem: Extraction failed for '{zip_path}': {e}")
            return None

    # --------------------------------------------------------------------------
    # SHELL INTEGRATION
    # --------------------------------------------------------------------------

    def open_file_explorer(self, path: str) -> None:
        """Execute the host OS native file explorer."""
        if not os.path.exists(path):
            logger.warning(f"FileSystem: Path does not exist: {path}")
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
            logger.error(f"FileSystem: Shell invocation failed: {e}")
            raise OSError(f"Could not open file explorer: {e}") from e