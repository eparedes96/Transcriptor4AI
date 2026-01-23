from __future__ import annotations

"""
Cache Repository Port Definition.

Defines the abstract interface for persistent caching of processed artifacts.
Enables the application to skip redundant processing of unchanged files
by mapping composite state hashes to previously generated content and metrics.
"""

from abc import ABC, abstractmethod
from typing import Optional, Tuple


# ==============================================================================
# CACHE REPOSITORY INTERFACE
# ==============================================================================
class ICacheRepository(ABC):
    """
    Contract for cache persistence providers.

    Any implementation (SQLite, JSON, Redis) must adhere to this interface
    to ensure the core pipeline remains infrastructure-agnostic.
    """

    @abstractmethod
    def get_entry(self, composite_hash: str) -> Optional[Tuple[str, int]]:
        """
        Retrieve a cached entry by its unique state identifier.

        Args:
            composite_hash: SHA-256 fingerprint combining file metadata and config.

        Returns:
            Optional[Tuple[str, int]]: A tuple containing (processed_content, token_count)
                                       if found, otherwise None.
        """
        pass

    @abstractmethod
    def set_entry(
            self,
            composite_hash: str,
            file_path: str,
            content: str,
            token_count: int
    ) -> None:
        """
        Persist a processed file result in the cache storage.

        Args:
            composite_hash: Unique identifier for the file state.
            file_path: Source filesystem path for traceability.
            content: The transformed source code or resource text.
            token_count: Calculated token density of the content.
        """
        pass

    @abstractmethod
    def purge_all(self) -> None:
        """
        Invalidate and remove all entries from the persistent storage.

        Used for manual maintenance or when global config changes require
        a full project re-transcription.
        """
        pass

    @abstractmethod
    def is_enabled(self) -> bool:
        """
        Check if the caching subsystem is operational and accessible.

        Returns:
            bool: True if the repository is ready for I/O operations.
        """
        pass