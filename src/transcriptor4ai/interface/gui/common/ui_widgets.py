from __future__ import annotations

"""
Interface Infrastructure Components.

Provides high-level technical utilities for the Graphical User Interface, 
including custom complex widgets and data transformation bridges between 
UI inputs and domain collections.
"""

import logging
from typing import Any, Callable, List, Optional

import customtkinter as ctk

from transcriptor4ai.shared import converters as conv

# Global logger initialization
logger = logging.getLogger(__name__)


# ==============================================================================
# DATA TRANSFORMATION BRIDGES
# ==============================================================================

def parse_list_from_string(value: Optional[str]) -> List[str]:
    """
    Bridge between raw UI text entry and domain string lists.

    Delegates to shared converters to ensure consistency between CLI and GUI.

    Args:
        value: Raw CSV input from a widget (e.g., ".py, .js").

    Returns:
        List[str]: Sanitized collection of tokens.
    """
    # 1. DELEGATE: Use standardized shared logic for parsing
    return conv.to_list_str(value)


# ==============================================================================
# CUSTOM UI COMPONENTS: SCROLLABLE DROPDOWN
# ==============================================================================

class CTkScrollableDropdown(ctk.CTkToplevel):
    """
    Advanced Dynamic Dropdown Menu.

    A theme-aware, scrollable overlay designed to handle large datasets
    (e.g., AI model lists) without impacting main window layout or
    overflowing the display area.
    """

    def __init__(
            self,
            attach: ctk.CTkBaseClass,
            values: List[str],
            command: Optional[Callable[[str], None]] = None,
            width: Optional[int] = None,
            height: int = 250,
            **kwargs: Any
    ) -> None:
        """
        Initialize the scrollable dropdown and anchor it to a parent widget.

        Args:
            attach: The widget acting as the trigger and anchor point.
            values: List of options to display.
            command: Selection callback (receives selected string).
            width: Widget width (defaults to anchor width).
            height: Maximum vertical size before scrolling.
        """
        super().__init__(takefocus=True)

        # 1. CONFIGURATION: Setup window properties for overlay behavior
        self.withdraw()  # Hide initially to prevent positioning flicker
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        # Retrieve system theme colors for seamless integration
        fg_color = ctk.ThemeManager.theme["CTkFrame"]["fg_color"]
        border_color = ctk.ThemeManager.theme["CTkFrame"]["border_color"]

        self._attach = attach
        self._values = values
        self._command = command
        self._width = width if width else attach.winfo_width()
        self._height = height

        # 2. STRUCTURE: Build the visual hierarchy
        self._main_container = ctk.CTkFrame(
            self,
            corner_radius=8,
            border_width=2,
            border_color=border_color,
            fg_color=fg_color
        )
        self._main_container.pack(expand=True, fill="both")

        self._scroll_frame = ctk.CTkScrollableFrame(
            self._main_container,
            width=self._width - 10,
            height=self._height - 10,
            corner_radius=6,
            fg_color="transparent"
        )
        self._scroll_frame.pack(padx=2, pady=2, expand=True, fill="both")

        # 3. POPULATE: Generate interactive items
        self._populate_values(values)

        # 4. LIFECYCLE: Bind events for auto-destruction and repositioning
        self.bind("<FocusOut>", lambda e: self._on_focus_out())
        self.bind("<Escape>", lambda e: self.destroy())

        # Ensure the dropdown follows the parent if the window moves/resizes
        self._attach.bind("<Configure>", lambda e: self._update_position(), add="+")

        # 5. RENDER: Initial positioning and visibility sequence
        self.after(1, self._update_position)
        self.after(10, self.deiconify)
        self.after(20, self.focus_set)

    def _populate_values(self, values: List[str]) -> None:
        """Construct the interactive button list from raw data."""
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
        """Calculate and apply absolute screen coordinates for anchoring."""
        if not self.winfo_exists():
            return

        # Force sync of internal geometry metrics
        self._attach.update_idletasks()

        # Resolve global screen coordinates of the anchor widget
        x = self._attach.winfo_rootx()
        y = self._attach.winfo_rooty() + self._attach.winfo_height() + 4

        # Apply geometry: Width x Height + X + Y
        self.geometry(f"{self._width}x{self._height}+{x}+{y}")

    def _on_item_click(self, value: str) -> None:
        """Notify observers and destroy the overlay on selection."""
        logger.debug(f"UI: Option selected -> {value}")
        if self._command:
            self._command(value)
        self.destroy()

    def _on_focus_out(self) -> None:
        """Handle menu closing when user clicks outside the component."""
        # Short delay to allow click events on internal buttons to register
        self.after(150, self._safe_destroy)

    def _safe_destroy(self) -> None:
        """Verify focus state before performing destruction."""
        if self.winfo_exists():
            focused_widget = self.focus_get()
            # Only destroy if focus has truly left the component hierarchy
            if focused_widget is None or not str(focused_widget).startswith(str(self)):
                self.destroy()