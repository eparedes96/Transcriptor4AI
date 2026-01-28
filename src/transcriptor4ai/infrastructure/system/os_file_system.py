from __future__ import annotations

"""
FileSystem Infrastructure Adapter (Main Facade).

This module implements the IFileSystem port by orchestrating specialized 
sub-services for IO management, path resolution, and system shell integration.
It serves as the single point of contact for the application's core logic
regarding host filesystem interactions.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.domain.ports.system_port import IFileSystem
from transcriptor4ai.infrastructure.system.fs.archive_handler import unpack_executable_from_zip
from transcriptor4ai.infrastructure.system.fs.io_manager import (
    check_existing_output_files,
    delete_file,
    directory_exists,
    file_exists,
    move_file,
    read_file_content,
    safe_mkdir,
    write_text_file,
)
from transcriptor4ai.infrastructure.system.fs.path_resolver import (
    get_expected_filenames,
    get_pricing_cache_path,
    get_real_output_path,
    get_user_data_dir,
    normalize_path,
)
from transcriptor4ai.infrastructure.system.fs.pipeline_io import (
    build_staging_paths,
    deploy_pipeline_artifacts,
    generate_unified_file,
)
from transcriptor4ai.infrastructure.system.fs.shell_utils import open_file_explorer_cmd

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# FILESYSTEM ADAPTER IMPLEMENTATION
# ==============================================================================

class FileSystemAdapter(IFileSystem):
    """
    Concrete implementation of IFileSystem.

    Functions as a high-level API that delegates technical execution
    to granular, testable sub-modules within the fs/ package.
    """

    # --- PATH & ARTIFACT RESOLUTION ---
    def get_expected_filenames(self, cfg: Dict[str, Any], prefix: str) -> List[str]:
        return get_expected_filenames(cfg, prefix)

    def build_staging_paths(
            self,
            staging_dir: str,
            prefix: str,
            tree_override: Optional[str] = None
    ) -> Dict[str, str]:
        return build_staging_paths(staging_dir, prefix, tree_override)

    def get_user_data_dir(self) -> str:
        return get_user_data_dir()

    def get_pricing_cache_path(self) -> str:
        return get_pricing_cache_path()

    def normalize_path(self, path: Optional[str], fallback: str) -> str:
        return normalize_path(path, fallback)

    def get_real_output_path(self, output_base_dir: str, output_subdir_name: str) -> str:
        return get_real_output_path(output_base_dir, output_subdir_name)

    # --- ATOMIC IO OPERATIONS ---
    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
        return check_existing_output_files(output_dir, names)

    def file_exists(self, path: str) -> bool:
        return file_exists(path)

    def directory_exists(self, path: str) -> bool:
        return directory_exists(path)

    def read_file_content(self, path: str) -> str:
        return read_file_content(path)

    def write_text_file(self, path: str, content: str) -> None:
        write_text_file(path, content)

    def safe_mkdir(self, path: str) -> Tuple[bool, Optional[str]]:
        return safe_mkdir(path)

    def delete_file(self, path: str) -> bool:
        return delete_file(path)

    def move_file(self, src: str, dst: str) -> bool:
        return move_file(src, dst)

    # --- PIPELINE WORKFLOW ---
    def generate_unified_file(
            self,
            output_path: str,
            base_path: str,
            tree_path: Optional[str],
            category_paths: Dict[str, str]
    ) -> bool:
        return generate_unified_file(output_path, base_path, tree_path, category_paths)

    def deploy_pipeline_artifacts(
            self,
            staging_paths: Dict[str, str],
            final_dir: str,
            prefix: str,
            unified_ok: bool,
            results_map: Dict[str, str]
    ) -> None:
        deploy_pipeline_artifacts(staging_paths, final_dir, prefix, unified_ok, results_map)

    # --- INTEGRATION & SHELL ---
    def unpack_executable_from_zip(self, zip_path: str, extract_to: str) -> Optional[str]:
        return unpack_executable_from_zip(zip_path, extract_to)

    def open_file_explorer(self, path: str) -> None:
        open_file_explorer_cmd(path)


# ==============================================================================
# COMPATIBILITY WRAPPERS (LEGACY SUPPORT)
# ==============================================================================

def open_file_explorer(path: str) -> None:
    """
    Stand-alone wrapper for UI components requiring direct access
    without adapter instantiation.
    """
    open_file_explorer_cmd(path)