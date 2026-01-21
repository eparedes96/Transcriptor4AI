from __future__ import annotations

"""
Tkinter Technical Utilities and OS Integration.

Provides high-level helpers for graphical user interface operations, including 
cross-platform filesystem exploration, CSV-to-list data transformation 
for user input fields, and custom scrollable components for large datasets.
"""

import logging
import os
import platform
import subprocess
import tkinter
from tkinter import messagebox as mb
from typing import Any, Callable, List, Optional

import customtkinter as ctk

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


# -----------------------------------------------------------------------------
# CUSTOM UI COMPONENTS: SCROLLABLE DROPDOWN
# -----------------------------------------------------------------------------

class CTkScrollableDropdown(ctk.CTkToplevel):
    """
    Custom Dropdown implementation featuring a Scrollbar for large datasets.

    Solves the overflow issue in standard ctk.CTkComboBox by using a
    Toplevel window anchored to a parent widget, containing a scrollable
    frame with interactive items.
    """

    def __init__(
            self,
            attach: ctk.CTkBaseClass,
            values: List[str],
            command: Optional[Callable[[str], None]] = None,
            width: Optional[int] = None,
            height: int = 200,
            **kwargs: Any
    ):
        """
        Initialize the scrollable dropdown.

        Args:
            attach: The widget to which the dropdown will be anchored.
            values: List of strings to display.
            command: Callback executed when an item is selected.
            width: Width of the dropdown (defaults to anchor width).
            height: Maximum height of the scrollable area.
        """
        super().__init__(takefocus=True)

        self.focus()
        self.attributes("-topmost", True)
        self.lift()
        self.withdraw()
        self.overrideredirect(True)

        self._attach = attach
        self._values = values
        self._command = command
        self._width = width if width else attach.winfo_width()
        self._height = height

        # Setup container with scrollbar
        self._frame = ctk.CTkScrollableFrame(
            self,
            width=self._width,
            height=self._height,
            corner_radius=0,
            fg_color="transparent"
        )
        self._frame.pack(expand=True, fill="both")

        self._populate_values(values)

        # Event bindings for lifecycle management
        self.bind("<FocusOut>", lambda e: self._on_focus_out())
        self._attach.bind("<Configure>", lambda e: self._update_position(), add="+")

        # Initial draw logic
        self.after(10, self._update_position)
        self.after(10, self.deiconify)

    def _populate_values(self, values: List[str]) -> None:
        """Create interactive buttons for each data entry."""
        for val in values:
            btn = ctk.CTkButton(
                self._frame,
                text=val,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                corner_radius=0,
                height=28,
                command=lambda v=val: self._on_item_click(v)
            )
            btn.pack(fill="x", expand=True)

    def _update_position(self) -> None:
        """Dynamically anchor the dropdown window below the parent widget."""
        if not self.winfo_exists():
            return

        x = self._attach.winfo_rootx()
        y = self._attach.winfo_rooty() + self._attach.winfo_height() + 2

        # Ensure correct scaling on High-DPI displays
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")

    def _on_item_click(self, value: str) -> None:
        """Handle selection event and notify controller."""
        logger.debug(f"UI: Scrollable Dropdown selection -> {value}")
        if self._command:
            self._command(value)
        self.destroy()

    def _on_focus_out(self) -> None:
        """Auto-close the dropdown when clicking outside its bounds."""
        # Small delay to allow click events on buttons to process first
        self.after(100, self.destroy)