from __future__ import annotations

"""
FileSystem Infrastructure Adapter.

Provides a concrete implementation of the IFileSystem port using standard 
OS libraries. Handles path normalization, atomic file operations, directory 
management, and integration with host shell and archive utilities.
"""

import logging
import os
import platform
import shutil
import subprocess
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.shared import constants as const

# Standardized logger for infrastructure operations
logger = logging.getLogger(__name__)

# ==============================================================================
# GLOBALS AND CONFIGURATION
# ==============================================================================

DEFAULT_OUTPUT_SUBDIR = "transcript"
APP_DIR_NAME = "Transcriptor4AI"
UNIX_APP_DIR_NAME = ".transcriptor4ai"


# ==============================================================================
# FILESYSTEM ADAPTER
# ==============================================================================

class FileSystemAdapter(IFileSystem):
    """
    Adapter for OS-level file, directory, and archive operations.
    """

    # --------------------------------------------------------------------------
    # ARTIFACT MAPPING & STAGING
    # --------------------------------------------------------------------------

    def get_expected_filenames(self, cfg: Dict[str, Any], prefix: str) -> List[str]:
        """
        Determine expected pipeline filenames based on configuration flags.

        Args:
            cfg: Application configuration dictionary.
            prefix: User-defined output prefix.

        Returns:
            List[str]: List of expected filenames.
        """
        files: List[str] = []

        # 1. INDIVIDUAL FILES: Map flags to specific category filenames
        if cfg.get("create_individual_files"):
            if cfg.get("process_modules"):
                files.append(f"{prefix}_modules.txt")
            if cfg.get("process_tests"):
                files.append(f"{prefix}_tests.txt")
            if cfg.get("process_resources"):
                files.append(f"{prefix}_resources.txt")
            if cfg.get("generate_tree"):
                files.append(f"{prefix}_tree.txt")

        # 2. AGGREGATES: Map unified and log artifacts
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
    ) -> Dict[str, str]:
        """
        Construct absolute filesystem paths for pipeline staging artifacts.
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
    # DIRECTORY RESOLUTION & NORMALIZATION
    # --------------------------------------------------------------------------

    def get_user_data_dir(self) -> str:
        """
        Resolve the OS-specific directory for persistent application data.

        Returns:
            str: Normalized absolute path to the data directory.
        """
        path: str = ""

        # 1. WINDOWS: Target LocalAppData or AppData
        if os.name == "nt":
            base = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
            if base:
                path = os.path.join(base, APP_DIR_NAME)

        # 2. UNIX/FALLBACK: Target hidden directory in user home
        if not path:
            home = os.path.expanduser("~")
            path = os.path.join(home, UNIX_APP_DIR_NAME)

        # 3. ENSURE: Create directory if absent
        os.makedirs(path, exist_ok=True)
        return os.path.abspath(path)

    def get_pricing_cache_path(self) -> str:
        """Resolve the persistent path for model pricing metadata."""
        return os.path.join(self.get_user_data_dir(), const.LOCAL_PRICING_FILENAME)

    def normalize_path(self, path: Optional[str], fallback: str) -> str:
        """
        Sanitize and expand filesystem paths.

        Args:
            path: Target raw path.
            fallback: Default path if target is empty.
        """
        p = (path or "").strip() or fallback

        try:
            # 1. EXPAND: Resolve user shortcuts (~) and environment variables
            p = os.path.expandvars(os.path.expanduser(p))
            return os.path.abspath(p)
        except Exception as e:
            logger.debug(f"PathNormalization: Resolution failed for '{p}': {e}")
            return os.path.abspath(fallback)

    def get_real_output_path(self, output_base_dir: str, output_subdir_name: str) -> str:
        """Resolve the final artifact destination directory."""
        sub = (output_subdir_name or "").strip() or DEFAULT_OUTPUT_SUBDIR
        return os.path.join(output_base_dir, sub)

    # --------------------------------------------------------------------------
    # CORE FILESYSTEM OPERATIONS
    # --------------------------------------------------------------------------

    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
        """Identify naming collisions in a target directory."""
        return [
            os.path.join(output_dir, n)
            for n in names if os.path.exists(os.path.join(output_dir, n))
        ]

    def file_exists(self, path: str) -> bool:
        """Check if target exists and is a regular file."""
        return os.path.isfile(path)

    def directory_exists(self, path: str) -> bool:
        """Check if target exists and is a directory."""
        return os.path.isdir(path)

    def read_file_content(self, path: str) -> str:
        """Read text content with high encoding resilience."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()

    def write_text_file(self, path: str, content: str) -> None:
        """
        Persist text data to disk with automatic parent resolution.
        """
        # 1. DIRECTORY: Ensure target hierarchy exists
        parent = os.path.dirname(os.path.abspath(path))
        if parent:
            os.makedirs(parent, exist_ok=True)

        # 2. I/O: Execute UTF-8 encoded write
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
        except OSError as e:
            logger.error(f"IOError: Failed to write text file at '{path}': {e}")
            raise

    def safe_mkdir(self, path: str) -> Tuple[bool, Optional[str]]:
        """Safely create directory hierarchy."""
        try:
            os.makedirs(path, exist_ok=True)
            return True, None
        except OSError as e:
            return False, str(e)

    def delete_file(self, path: str) -> bool:
        """Remove file from system if present."""
        if not os.path.exists(path):
            return True
        try:
            os.remove(path)
            return True
        except OSError as e:
            logger.error(f"FileSystem: Deletion failed for '{path}': {e}")
            return False

    def move_file(self, src: str, dst: str) -> bool:
        """Atomically transition file to a new location."""
        try:
            if os.path.exists(dst):
                os.remove(dst)
            shutil.move(src, dst)
            return True
        except OSError as e:
            logger.error(f"FileSystem: Move failed from '{src}' to '{dst}': {e}")
            return False

    # --------------------------------------------------------------------------
    # PIPELINE ARTIFACT MANAGEMENT
    # --------------------------------------------------------------------------

    def generate_unified_file(
            self,
            output_path: str,
            base_path: str,
            tree_path: Optional[str],
            category_paths: Dict[str, str]
    ) -> bool:
        """
        Compile multiple artifacts into a single LLM-optimized context file.
        """
        try:
            with open(output_path, "w", encoding="utf-8") as outfile:
                # 1. HEADER: Define project identity
                base_name = os.path.basename(base_path)
                outfile.write(f"PROJECT CONTEXT: {base_name}\n" + "=" * 80 + "\n\n")

                # 2. STRUCTURE: Append tree if available
                if tree_path and os.path.exists(tree_path):
                    outfile.write("PROJECT STRUCTURE:\n" + "-" * 50 + "\n")
                    with open(tree_path, "r", encoding="utf-8") as infile:
                        shutil.copyfileobj(infile, outfile)
                    outfile.write("\n\n")

                # 3. CONTENT: Stream categorized module data
                for key in ["modules", "tests", "resources"]:
                    path = category_paths.get(key)
                    if path and os.path.exists(path):
                        with open(path, "r", encoding="utf-8") as infile:
                            shutil.copyfileobj(infile, outfile)
                        outfile.write("\n\n")
            return True

        except OSError as e:
            logger.error(f"PipelineIO: Aggregation failed: {e}")
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
        Finalize deployment by moving files from staging to user directory.
        """
        # 1. UNIFIED: Finalize core context file
        if unified_ok:
            dest_unified = os.path.join(final_dir, f"{prefix}_full_context.txt")
            src_unified = staging_paths["unified"]

            if os.path.abspath(src_unified) != os.path.abspath(dest_unified):
                if self.move_file(src_unified, dest_unified):
                    results_map["unified"] = dest_unified
            else:
                results_map["unified"] = dest_unified

        # 2. ERRORS: Finalize diagnostic logs
        err_staging = staging_paths.get("errors")
        if err_staging and os.path.exists(err_staging):
            dest_errors = os.path.join(final_dir, f"{prefix}_errors.txt")
            if os.path.abspath(err_staging) != os.path.abspath(dest_errors):
                self.move_file(err_staging, dest_errors)

    # --------------------------------------------------------------------------
    # ARCHIVE & UPDATE INTEGRATION
    # --------------------------------------------------------------------------

    def unpack_executable_from_zip(self, zip_path: str, extract_to: str) -> Optional[str]:
        """
        Extract binary components from update archives.
        """
        if not zipfile.is_zipfile(zip_path):
            logger.error(f"UpdateIO: Invalid ZIP archive -> {zip_path}")
            return None

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                # 1. DISCOVERY: Filter for executables
                exe_files = [f for f in zf.namelist() if f.lower().endswith(".exe")]
                if not exe_files:
                    return None

                # 2. HEURISTIC: Find main application binary
                target = next((f for f in exe_files if "transcriptor" in f.lower()), exe_files[0])

                # 3. EXTRACTION: Securely extract to target path
                zf.extract(target, extract_to)
                return os.path.join(extract_to, target)

        except (zipfile.BadZipFile, OSError) as e:
            logger.error(f"UpdateIO: Extraction failure: {e}")
            return None

    # --------------------------------------------------------------------------
    # SHELL & GUI INTEGRATION
    # --------------------------------------------------------------------------

    def open_file_explorer(self, path: str) -> None:
        """Trigger host-specific file manager for a given path."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path not found: {path}")

        sys_name = platform.system()
        try:
            if sys_name == "Windows":
                os.startfile(path)
            elif sys_name == "Darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            raise OSError(f"SystemExplorer: Shell invocation failed: {e}")


# ==============================================================================
# COMPATIBILITY WRAPPERS (LEGACY)
# ==============================================================================

def open_file_explorer(path: str) -> None:
    """Standalone wrapper for direct shell access."""
    FileSystemAdapter().open_file_explorer(path)