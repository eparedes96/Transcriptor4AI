from __future__ import annotations

"""
GUI Dialog and Interaction Helpers.

Provides reusable utilities for common graphical user interface tasks, 
such as directory discovery and cross-widget synchronization, specifically 
designed for CustomTkinter environments.
"""

import logging
from typing import Optional

import customtkinter as ctk

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# DIRECTORY SELECTION UTILITIES
# ==============================================================================

def browse_directory(
        app: ctk.CTk,
        entry_widget: ctk.CTkEntry,
        linked_entry: Optional[ctk.CTkEntry] = None
) -> None:
    """
    Prompt user for directory selection and synchronize related entry widgets.

    Args:
        app: Root application instance acting as the modal parent.
        entry_widget: The primary entry widget to be updated with the path.
        linked_entry: Optional secondary widget (e.g., output path)
                      to keep in sync.
    """
    # 1. INTERACTION: Open native directory picker
    path: str = ctk.filedialog.askdirectory(parent=app, title="Select Directory")

    if path:
        logger.debug(f"DialogHelpers: User selected path -> {path}")

        # 2. UPDATE PRIMARY: Temporarily enable widget to modify content
        _update_entry_content(entry_widget, path)

        # 3. SYNCHRONIZATION: Automatically update linked field if provided
        if linked_entry:
            _update_entry_content(linked_entry, path)


# ==============================================================================
# PRIVATE UI HELPERS
# ==============================================================================

def _update_entry_content(widget: ctk.CTkEntry, content: str) -> None:
    """
    Safely overwrite the content of a CTkEntry regardless of its current state.
    """
    # Bypass readonly constraints
    widget.configure(state="normal")

    # Perform clear and insert
    widget.delete(0, "end")
    widget.insert(0, content)

    # Restore readonly state for data integrity
    widget.configure(state="readonly")