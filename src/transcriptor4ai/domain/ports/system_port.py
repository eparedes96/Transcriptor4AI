from __future__ import annotations

"""
FileSystem Infrastructure Port.

Defines the abstract interface for host operating system operations, including 
file manipulation, directory resolution, and shell integration. This contract 
ensures the core application logic remains decoupled from specific OS 
implementations and filesystem libraries.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple


class IFileSystem(ABC):
    """
    Contract for OS-level file, directory, and shell operations.
    """

    # ==========================================================================
    # PATH RESOLUTION & DISCOVERY
    # ==========================================================================

    @abstractmethod
    def get_user_data_dir(self) -> str:
        """Resolve the persistent application data directory."""
        pass

    @abstractmethod
    def get_pricing_cache_path(self) -> str:
        """Resolve the path for the pricing cache file."""
        pass

    @abstractmethod
    def normalize_path(self, path: Optional[str], fallback: str) -> str:
        """
        Normalize a path handling environment variables and shortcuts.

        Args:
            path: Input path string or None.
            fallback: Default path to use if input is invalid.
        """
        pass

    @abstractmethod
    def get_real_output_path(self, output_base_dir: str, output_subdir_name: str) -> str:
        """Calculate the final destination path for artifacts."""
        pass

    @abstractmethod
    def get_expected_filenames(self, cfg: Dict[str, Any], prefix: str) -> List[str]:
        """
        Determine the standard filenames that the pipeline expects to generate.

        Args:
            cfg: Active session configuration dictionary.
            prefix: User-defined output prefix.
        """
        pass

    @abstractmethod
    def build_staging_paths(
            self,
            staging_dir: str,
            prefix: str,
            tree_override: Optional[str] = None
    ) -> Dict[str, str]:
        """Construct absolute paths for pipeline staging artifacts."""
        pass

    # ==========================================================================
    # FILESYSTEM MANIPULATION
    # ==========================================================================

    @abstractmethod
    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
        """Identify naming collisions in a target directory."""
        pass

    @abstractmethod
    def safe_mkdir(self, path: str) -> Tuple[bool, Optional[str]]:
        """Create a directory hierarchy safely."""
        pass

    @abstractmethod
    def delete_file(self, path: str) -> bool:
        """Remove a file from the system."""
        pass

    @abstractmethod
    def directory_exists(self, path: str) -> bool:
        """Check if a path exists and is a directory."""
        pass

    @abstractmethod
    def file_exists(self, path: str) -> bool:
        """Check if a path exists and is a file."""
        pass

    # ==========================================================================
    # DATA I/O OPERATIONS
    # ==========================================================================

    @abstractmethod
    def read_file_content(self, path: str) -> str:
        """Read the entire content of a file with encoding resilience."""
        pass

    @abstractmethod
    def write_text_file(self, path: str, content: str) -> None:
        """
        Persist a string to a file using UTF-8 encoding.

        Args:
            path: Absolute filesystem destination.
            content: The text data to persist.
        """
        pass

    @abstractmethod
    def move_file(self, src: str, dst: str) -> bool:
        """Atomically move a file across the filesystem."""
        pass

    # ==========================================================================
    # ADVANCED OS INTEGRATION
    # ==========================================================================

    @abstractmethod
    def generate_unified_file(
            self,
            output_path: str,
            base_path: str,
            tree_path: Optional[str],
            category_paths: Dict[str, str]
    ) -> bool:
        """Stream and aggregate multiple artifacts into a single context."""
        pass

    @abstractmethod
    def deploy_pipeline_artifacts(
            self,
            staging_paths: Dict[str, str],
            final_dir: str,
            prefix: str,
            unified_ok: bool,
            results_map: Dict[str, str]
    ) -> None:
        """Transition files from staging area to final destination."""
        pass

    @abstractmethod
    def unpack_executable_from_zip(self, zip_path: str, extract_to: str) -> Optional[str]:
        """Extract the application binary from a compressed update."""
        pass

    @abstractmethod
    def open_file_explorer(self, path: str) -> None:
        """Trigger the host OS native file explorer."""
        pass