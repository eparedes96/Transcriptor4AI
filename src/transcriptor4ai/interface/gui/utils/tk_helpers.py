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
    Professional Scrollable Dropdown Menu.

    A theme-aware, border-rounded dropdown that handles large datasets with
    a functional slider. Designed to mimic native ComboBox behavior without
    the vertical overflow limitations.
    """

    def __init__(
            self,
            attach: ctk.CTkBaseClass,
            values: List[str],
            command: Optional[Callable[[str], None]] = None,
            width: Optional[int] = None,
            height: int = 250,
            **kwargs: Any
    ):
        """
        Initialize the scrollable dropdown with native styling.

        Args:
            attach: The widget to which the dropdown will be anchored.
            values: List of strings to display.
            command: Callback executed when an item is selected.
            width: Width of the dropdown (defaults to anchor width).
            height: Maximum height of the scrollable area.
        """
        super().__init__(takefocus=True)

        # 1. Basic Window Configuration
        self.withdraw()  # Avoid flicker during positioning
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Ensure we adapt to the current theme colors
        fg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        border_color = ctk.ThemeManager.theme["CTkFrame"]["border_color"]

        self._attach = attach
        self._values = values
        self._command = command
        self._width = width if width else attach.winfo_width()
        self._height = height

        # 2. Styling Container (The Border & Background)
        self._main_container = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=2,
            border_color=border_color,
            fg_color=fg_color
        )
        self._main_container.pack(expand=True, fill="both")

        # 3. The Scrollable Content Area
        self._scroll_frame = ctk.CTkScrollableFrame(
            self._main_container,
            width=self._width - 10,
            height=self._height - 10,
            corner_radius=6,
            fg_color="transparent"
        )
        self._scroll_frame.pack(padx=2, pady=2, expand=True, fill="both")

        self._populate_values(values)

        # 4. Lifecycle Bindings
        self.bind("<FocusOut>", lambda e: self._on_focus_out())
        self.bind("<Escape>", lambda e: self.destroy())
        self._attach.bind("<Configure>", lambda e: self._update_position(), add="+")

        # Initial render sequence
        self.after(1, self._update_position)
        self.after(10, self.deiconify)
        self.after(20, self.focus_set)

    def _populate_values(self, values: List[str]) -> None:
        """Create high-fidelity interactive buttons for the menu."""
        for val in values:
            btn = ctk.CTkButton(
                self._scroll_frame,
                text=val,
                anchor="w",
                fg_color="transparent",
                text_color=("gray10", "gray90"),
                hover_color=("gray75", "gray25"),
                corner_radius=4,
                height=30,
                font=ctk.CTkFont(size=12),
                command=lambda v=val: self._on_item_click(v)
            )
            btn.pack(fill="x", expand=True, padx=2, pady=1)

    def _update_position(self) -> None:
        """Calculate coordinates to anchor the menu exactly below the parent."""
        if not self.winfo_exists():
            return

        # Force geometry update to ensure winfo values are accurate
        self._attach.update_idletasks()

        x = self._attach.winfo_rootx()
        y = self._attach.winfo_rooty() + self._attach.winfo_height() + 4

        # Construct geometry string (Width x Height + X + Y)
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")

    def _on_item_click(self, value: str) -> None:
        """Handle selection and notify observers."""
        logger.debug(f"UI: Menu Selection -> {value}")
        if self._command:
            self._command(value)
        self.destroy()

    def _on_focus_out(self) -> None:
        """Gracefully close the menu when focus is lost."""
        # We check if the focus moved to one of our internal buttons
        # before self-destructing to avoid race conditions.
        self.after(150, self._safe_destroy)

    def _safe_destroy(self) -> None:
        """Conditional destruction to ensure click events are registered."""
        if self.winfo_exists():
            # Check if focus is still within this toplevel or its children
            focused_widget = self.focus_get()
            if focused_widget is None or not str(focused_widget).startswith(str(self)):
                self.destroy()