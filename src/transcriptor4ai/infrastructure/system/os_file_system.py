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
from typing import List, Optional, Tuple, Any, Dict

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
    # PATH MANIPULATION & ARTIFACT MAPPING
    # --------------------------------------------------------------------------

    def get_expected_filenames(self, cfg: dict[str, Any], prefix: str) -> list[str]:
        """
        Determine the standard filenames that the pipeline expects to generate
        based on the provided configuration flags.
        """
        files: list[str] = []

        # 1. PROCESS: Map individual categorized artifacts
        if cfg.get("create_individual_files"):
            if cfg.get("process_modules"):
                files.append(f"{prefix}_modules.txt")
            if cfg.get("process_tests"):
                files.append(f"{prefix}_tests.txt")
            if cfg.get("process_resources"):
                files.append(f"{prefix}_resources.txt")
            if cfg.get("generate_tree"):
                files.append(f"{prefix}_tree.txt")

        # 2. PROCESS: Map aggregate artifacts
        if cfg.get("create_unified_file"):
            files.append(f"{prefix}_full_context.txt")

        if cfg.get("save_error_log"):
            files.append(f"{prefix}_errors.txt")

        return files

    def build_staging_paths(
            self,
            staging_dir: str,
            prefix: str,
            tree_override: Optional[str] = None
    ) -> dict[str, str]:
        """
        Construct absolute filesystem paths for all pipeline staging artifacts.
        """
        return {
            "modules": os.path.join(staging_dir, f"{prefix}_modules.txt"),
            "tests": os.path.join(staging_dir, f"{prefix}_tests.txt"),
            "resources": os.path.join(staging_dir, f"{prefix}_resources.txt"),
            "tree": tree_override or os.path.join(staging_dir, f"{prefix}_tree.txt"),
            "errors": os.path.join(staging_dir, f"{prefix}_errors.txt"),
            "unified": os.path.join(staging_dir, f"{prefix}_full_context.txt"),
        }

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

    def file_exists(self, path: str) -> bool:
        """Verify if a specific path points to an existing file."""
        return os.path.isfile(path)

    def read_file_content(self, path: str) -> str:
        """Read the entire content of a file with encoding resilience."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def path_join(self, *args: str) -> str:
        """Encapsulate OS-specific path concatenation."""
        return os.path.join(*args)

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

    def move_file(self, src: str, dst: str) -> bool:
        """
        Perform an atomic file move operation across the filesystem.
        """
        try:
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
            return True
        except OSError as e:
            logger.error(f"FileSystem: Failed to move '{src}' to '{dst}': {e}")
            return False

    # --------------------------------------------------------------------------
    # PIPELINE ARTIFACT ORCHESTRATION
    # --------------------------------------------------------------------------

    def generate_unified_file(
        self,
        output_path: str,
        base_path: str,
        tree_path: Optional[str],
        category_paths: Dict[str, str]
    ) -> bool:
        """
        Stream and concatenate multiple staging files into a single context.
        """
        try:
            with open(output_path, "w", encoding="utf-8") as outfile:
                # 1. WRITE: Root Header
                base_name = os.path.basename(base_path)
                outfile.write(f"PROJECT CONTEXT: {base_name}\n" + "=" * 80 + "\n\n")

                # 2. WRITE: Directory Tree Section
                if tree_path and os.path.exists(tree_path):
                    outfile.write("PROJECT STRUCTURE:\n" + "-" * 50 + "\n")
                    with open(tree_path, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                # 3. WRITE: Categorized Content Sections
                for key in ["modules", "tests", "resources"]:
                    path = category_paths.get(key)
                    if path and os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as infile:
                            shutil.copyfileobj(infile, outfile)
                        outfile.write("\n\n")

            return True
        except OSError as e:
            logger.error(f"FileSystem: Failed to aggregate unified file: {e}")
            return False

    def deploy_pipeline_artifacts(
        self,
        staging_paths: Dict[str, str],
        final_dir: str,
        prefix: str,
        unified_ok: bool,
        results_map: Dict[str, str]
    ) -> None:
        """
        Transition processed files from staging area to the final user directory.
        """
        # 1. PROCESS: Unified Context deployment
        if unified_ok:
            dest_unified = os.path.join(final_dir, f"{prefix}_full_context.txt")
            if self.move_file(staging_paths["unified"], dest_unified):
                results_map["unified"] = dest_unified

        # 2. PROCESS: Error log deployment (only if generated in different area)
        err_staging = staging_paths.get("errors")
        if err_staging and os.path.exists(err_staging):
            dest_errors = os.path.join(final_dir, f"{prefix}_errors.txt")
            if os.path.abspath(err_staging) != os.path.abspath(dest_errors):
                self.move_file(err_staging, dest_errors)

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

# ==============================================================================
# STANDALONE COMPATIBILITY WRAPPERS
# ==============================================================================

def open_file_explorer(path: str) -> None:
    """
    Standalone wrapper for the FileSystemAdapter's shell integration.

    Used by UI dialogs (like results_modal) that require direct system access
    without passing the full DI container.
    """
    adapter = FileSystemAdapter()
    adapter.open_file_explorer(path)