from __future__ import annotations

"""
Model Registry Port Definition.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class IModelRegistry(ABC):
    """
    Contract for AI model metadata and pricing providers.
    """

    @abstractmethod
    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """Retrieve the catalog of all discovered models."""
        pass

    @abstractmethod
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Fetch normalized metadata for a specific model."""
        pass

    @abstractmethod
    def sync_remote(self) -> bool:
        """Execute a synchronization cycle with the remote authority."""
        pass