from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Tuple, Optional


@functools.lru_cache(maxsize=1)
def _get_user_info() -> Tuple[Optional[str], Optional[str]]:
    """
    Retrieve OS-level user metadata with memoization.

    Detects the current username and home directory path to build
    anonymization rules. Cached to prevent expensive OS calls during
    high-volume stream processing.

    Returns:
        Tuple[Optional[str], Optional[str]]: A tuple containing (Username, HomeDirectory).
    """
    user_name: Optional[str] = None
    home_dir: Optional[str] = None

    try:
        user_name = os.getlogin()
    except Exception:
        try:
            user_name = os.environ.get("USER") or os.environ.get("USERNAME")
        except Exception:
            pass

    try:
        home_path = Path.home()
        home_dir = str(home_path).replace("\\", "/")
    except Exception:
        pass

    return user_name, home_dir
