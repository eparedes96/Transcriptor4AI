from __future__ import annotations

"""
FileSystem Infrastructure Adapter.

Acts as a Facade orchestrating specialized internal modules (IO, Paths, Shell)
to fulfill the IFileSystem port contract.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from transcriptor4ai.domain.ports.system_port import IFileSystem
from . import archive_handler as arch
from . import io_manager as io
from . import path_resolver as path
from . import pipeline_io as pipe
from . import shell_utils as shell

logger = logging.getLogger(__name__)

# ==============================================================================
# ADAPTER IMPLEMENTATION
# ==============================================================================

class FileSystemAdapter(IFileSystem):
    """
    High-level entry point for OS operations.
    Delegates atomic responsibilities to internal sub-modules.
    """

    # --------------------------------------------------------------------------
    # PATH RESOLUTION
    # --------------------------------------------------------------------------

    def get_user_data_dir(self) -> str:
        return path.get_user_data_dir()

    def get_pricing_cache_path(self) -> str:
        return path.get_pricing_cache_path()

    def normalize_path(self, p: Optional[str], fallback: str) -> str:
        return path.normalize_path(p, fallback)

    def get_real_output_path(self, base: str, sub: str) -> str:
        return path.get_real_output_path(base, sub)

    def get_expected_filenames(self, cfg: Dict[str, Any], prefix: str) -> List[str]:
        return path.get_expected_filenames(cfg, prefix)

    # --------------------------------------------------------------------------
    # ATOMIC IO
    # --------------------------------------------------------------------------

    def file_exists(self, p: str) -> bool:
        return io.file_exists(p)

    def directory_exists(self, p: str) -> bool:
        return io.directory_exists(p)

    def read_file_content(self, p: str) -> str:
        return io.read_file_content(p)

    def write_text_file(self, p: str, content: str) -> None:
        return io.write_text_file(p, content)

    def safe_mkdir(self, p: str) -> Tuple[bool, Optional[str]]:
        return io.safe_mkdir(p)

    def delete_file(self, p: str) -> bool:
        return io.delete_file(p)

    def move_file(self, src: str, dst: str) -> bool:
        return io.move_file(src, dst)

    def check_existing_output_files(self, out_dir: str, names: List[str]) -> List[str]:
        return io.check_existing_output_files(out_dir, names)

    # --------------------------------------------------------------------------
    # PIPELINE SPECIFIC IO
    # --------------------------------------------------------------------------

    def build_staging_paths(self, s_dir: str, pref: str, tree: Optional[str] = None) -> Dict[str, str]:
        return pipe.build_staging_paths(s_dir, pref, tree)

    def generate_unified_file(self, out: str, base: str, tree: Optional[str], cats: Dict[str, str]) -> bool:
        return pipe.generate_unified_file(out, base, tree, cats)

    def deploy_pipeline_artifacts(self, s_paths: Dict[str, str], f_dir: str, pref: str, ok: bool, res_map: Dict[str, str]) -> None:
        return pipe.deploy_pipeline_artifacts(s_paths, f_dir, pref, ok, res_map)

    # --------------------------------------------------------------------------
    # ARCHIVE & SHELL INTEGRATION
    # --------------------------------------------------------------------------

    def unpack_executable_from_zip(self, zip_p: str, extract_t: str) -> Optional[str]:
        return arch.unpack_executable_from_zip(zip_p, extract_t)

    def open_file_explorer(self, p: str) -> None:
        return shell.open_file_explorer_cmd(p)