from __future__ import annotations

"""
User Context System Adapter.

Concrete implementation of the IUserContext port. Interacts with the underlying
Operating System to retrieve the current user's identity and home directory structure.
Uses memoization to minimize expensive IO calls during high-throughput operations.
"""

import functools
import logging
import os
from pathlib import Path
from typing import Optional, Tuple

from transcriptor4ai.domain.ports.user_port import IUserContext

logger = logging.getLogger(__name__)

# ==============================================================================
# SYSTEM ADAPTER IMPLEMENTATION
# ==============================================================================
class UserContextAdapter(IUserContext):
    """
    OS-agnostic provider for user metadata using standard library calls.
    """

    def get_username(self) -> Optional[str]:
        """Retrieve the cached system username."""
        return self._resolve_os_identity()[0]

    def get_home_directory(self) -> Optional[str]:
        """Retrieve the cached and normalized home directory path."""
        return self._resolve_os_identity()[1]

    def get_context_info(self) -> dict[str, Optional[str]]:
        """Retrieve the full user context map."""
        user, home = self._resolve_os_identity()
        return {
            "username": user,
            "home_dir": home
        }

    # ==========================================================================
    # INTERNAL RESOLUTION LOGIC
    # ==========================================================================
    @functools.lru_cache(maxsize=1)
    def _resolve_os_identity(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Execute the OS lookup logic with thread-safe caching.

        Strategies:
        1. Username: os.getlogin() -> env['USER'] -> env['USERNAME']
        2. Home: Path.home() -> Normalized to forward slashes for Regex compatibility.

        Returns:
            Tuple[Optional[str], Optional[str]]: (Username, HomeDir).
        """
        user_name: Optional[str] = None
        home_dir: Optional[str] = None

        # 1. RESOLVE USERNAME
        try:
            user_name = os.getlogin()
        except (OSError, AttributeError):
            # Fallback for environments without TTY (Docker, CI, detached processes)
            user_name = os.environ.get("USER") or os.environ.get("USERNAME")

        if not user_name:
            logger.debug("UserContext: Could not resolve username from OS or Environment.")

        # 2. RESOLVE HOME DIRECTORY
        try:
            home_path = Path.home()
            # Normalize Windows backslashes to forward slashes to simplify
            # downstream regex masking in the Sanitizer.
            home_dir = str(home_path).replace("\\", "/")
        except Exception as e:
            logger.warning(f"UserContext: Failed to resolve home directory: {e}")

        return user_name, home_dir