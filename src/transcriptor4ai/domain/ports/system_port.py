from __future__ import annotations

"""
FileSystem Port Definition.

Defines the abstract interface for OS-level file, directory, and shell 
operations. This contract ensures the Application layer remains agnostic 
of specific library implementations (os, pathlib, shutil).
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class IFileSystem(ABC):
    """
    Contract for OS-level file, directory, and shell operations.
    """

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
        """Normalize a path handling environment variables and shortcuts."""
        pass

    @abstractmethod
    def get_real_output_path(self, output_base_dir: str, output_subdir_name: str) -> str:
        """Calculate the final destination path for artifacts."""
        pass

    @abstractmethod
    def check_existing_output_files(self, output_dir: str, names: List[str]) -> List[str]:
        """Identify naming collisions in a directory."""
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

    # ==========================================================================
    # I/O OPERATIONS
    # ==========================================================================

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
    def unpack_executable_from_zip(self, zip_path: str, extract_to: str) -> Optional[str]:
        """Extract the application binary from a compressed update."""
        pass

    @abstractmethod
    def open_file_explorer(self, path: str) -> None:
        """Trigger the host OS native file explorer."""
        pass