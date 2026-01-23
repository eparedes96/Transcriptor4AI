from __future__ import annotations

"""
User Context Port Definition.

Defines the abstract interface for retrieving execution environment metadata
related to the current operating system user. This allows the application
to perform privacy-sensitive operations (like path masking) while remaining
agnostic to the underlying OS calls or environment variables.
"""

from abc import ABC, abstractmethod
from typing import Optional


# ==============================================================================
# USER CONTEXT INTERFACE
# ==============================================================================
class IUserContext(ABC):
    """
    Contract for user metadata providers.

    Implementations of this port are responsible for querying the host system
    to identify the current user's identity and personal directory structure.
    """

    @abstractmethod
    def get_username(self) -> Optional[str]:
        """
        Retrieve the login name of the current system user.

        Returns:
            Optional[str]: The system username (e.g., 'admin', 'root')
                           or None if the identifier cannot be resolved.
        """
        pass

    @abstractmethod
    def get_home_directory(self) -> Optional[str]:
        """
        Resolve the absolute path to the current user's home directory.

        Used by the sanitization engine to identify and mask local filesystem
        roots in the generated AI context.

        Returns:
            Optional[str]: Normalized absolute path to the user's home
                           or None if inaccessible.
        """
        pass

    @abstractmethod
    def get_context_info(self) -> dict[str, Optional[str]]:
        """
        Consolidate all user metadata into a structured dictionary.

        Returns:
            dict[str, Optional[str]]: A map containing 'username' and 'home_dir'.
        """
        pass