from __future__ import annotations

import logging
import os
import platform
import subprocess
from tkinter import messagebox as mb
from typing import Optional, List

from transcriptor4ai.utils.i18n import i18n

logger = logging.getLogger(__name__)


def open_file_explorer(path: str) -> None:
    """
    Open the host OS file explorer at the given path.
    Supports Windows, macOS, and Linux (xdg-open).

    Args:
        path: Directory path to open.
    """
    if not os.path.exists(path):
        logger.warning(f"Attempted to open non-existent path: {path}")
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
        logger.error(f"Failed to open file explorer: {e}")
        mb.showerror(i18n.t("gui.dialogs.error_title"), f"Could not open folder:\n{e}")


def parse_list_from_string(value: Optional[str]) -> List[str]:
    """
    Convert a comma-separated string to a list of stripped strings.

    Args:
        value: Input CSV string (e.g., ".py, .js").

    Returns:
        List of strings (e.g., [".py", ".js"]). Returns empty list on None.
    """
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]
