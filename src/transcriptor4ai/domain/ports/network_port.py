from __future__ import annotations

"""
Network Client Port Definition.
"""

from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, Optional, Tuple


class IUpdateClient(ABC):
    """
    Contract for application update discovery and acquisition.
    """

    @abstractmethod
    def check_for_updates(self, current_version: str) -> Dict[str, Any]:
        """Query for newer application releases."""
        pass

    @abstractmethod
    def download_binary_stream(
        self,
        url: str,
        dest_path: str,
        progress_callback: Optional[Callable[[float], None]] = None,
    ) -> Tuple[bool, str]:
        """Acquire a remote binary using buffered streaming."""
        pass