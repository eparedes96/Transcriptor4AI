from __future__ import annotations

"""
Configuration Repository Port Definition.

Provides the abstract interface for managing the persistence of application
state, user preferences, and configuration profiles. This contract ensures
that the application logic remains decoupled from the physical storage
mechanism (e.g., JSON files, databases, or cloud sync).
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


# ==============================================================================
# CONFIGURATION REPOSITORY INTERFACE
# ==============================================================================
class IConfigRepository(ABC):
    """
    Contract for configuration persistence providers.

    Responsible for the full lifecycle of settings, from the global app state
    to technology-specific user profiles.
    """

    @abstractmethod
    def load_app_state(self) -> Dict[str, Any]:
        """
        Retrieve the complete application state dictionary.

        Returns:
            Dict[str, Any]: The full state schema including app settings,
                            last session data, and saved profiles.
        """
        pass

    @abstractmethod
    def save_app_state(self, state: Dict[str, Any]) -> None:
        """
        Persist the entire application state to storage.

        Args:
            state: The complete state dictionary to be serialized.
        """
        pass

    @abstractmethod
    def load_config(self) -> Dict[str, Any]:
        """
        Extract the configuration for the active or last session.

        Returns:
            Dict[str, Any]: A sanitized configuration dictionary ready for
                            pipeline consumption.
        """
        pass

    @abstractmethod
    def save_config(self, config: Dict[str, Any]) -> None:
        """
        Persist the provided dictionary as the active session configuration.

        Args:
            config: The session-specific parameters to save.
        """
        pass

    @abstractmethod
    def save_profile(self, name: str, config: Dict[str, Any]) -> None:
        """
        Store a named configuration preset (profile).

        Args:
            name: Unique identifier for the profile.
            config: The configuration dictionary associated with the profile.
        """
        pass

    @abstractmethod
    def delete_profile(self, name: str) -> bool:
        """
        Remove a saved profile from persistent storage.

        Args:
            name: The name of the profile to delete.

        Returns:
            bool: True if the profile was found and deleted, False otherwise.
        """
        pass

    @abstractmethod
    def get_profile_names(self) -> List[str]:
        """
        Retrieve a list of all identifiers for currently saved profiles.

        Returns:
            List[str]: Alphabetical list of available profile names.
        """
        pass