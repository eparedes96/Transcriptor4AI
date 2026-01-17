from __future__ import annotations

"""
Tkinter Technical Utilities and OS Integration.

Provides high-level helpers for graphical user interface operations, including 
cross-platform filesystem exploration and CSV-to-list data transformation 
for user input fields.
"""

import logging
import os
import platform
import subprocess
from tkinter import messagebox as mb
from typing import Optional, List

from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# OS INTEGRATION API
# -----------------------------------------------------------------------------

def open_file_explorer(path: str) -> None:
    """
    Execute the host operating system's native file explorer.

    Supports Windows (explorer.exe), macOS (open), and Linux (xdg-open).
    Validates path existence before execution to prevent system-level exceptions.

    Args:
        path: Absolute directory path to open.
    """
    if not os.path.exists(path):
        logger.warning(f"UI Action: Attempted to open non-existent path: {path}")
        mb.showerror(i18n.t("gui.dialogs.error_title"), i18n.t("gui.popups.error_path", path=path))
        return

    try:
        sys_name = platform.system()
        if sys_name == "Windows":
            os.startfile(path)
        elif sys_name == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        logger.error(f"System Error: Failed to invoke file explorer: {e}")
        mb.showerror(i18n.t("gui.dialogs.error_title"), f"Could not open folder:\n{e}")

# -----------------------------------------------------------------------------
# DATA TRANSFORMATION HELPERS
# -----------------------------------------------------------------------------

def parse_list_from_string(value: Optional[str]) -> List[str]:
    """
    Transform a comma-separated user input string into a list of sanitized tokens.

    Trims leading and trailing whitespace from each element and discards
    empty segments to ensure clean configuration arrays.

    Args:
        value: Raw CSV string input from a widget (e.g., ".py, .js").

    Returns:
        List[str]: Collection of stripped strings. Returns empty list if input is None.
    """
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]