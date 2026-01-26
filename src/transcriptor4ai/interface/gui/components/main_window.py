from __future__ import annotations

"""
Main Application Window Factory.

Initializes the root CustomTkinter application window, configures global 
theme attributes, and establishes the primary structural grid for 
navigation and content rendering.
"""

from typing import Final

import customtkinter as ctk

from transcriptor4ai.shared import constants as const

# ==============================================================================
# UI CONSTANTS
# ==============================================================================
DEFAULT_GEOMETRY: Final[str] = "1000x700"
MIN_WIDTH: Final[int] = 800
MIN_HEIGHT: Final[int] = 600


# ==============================================================================
# ROOT WINDOW FACTORY
# ==============================================================================

def create_main_window() -> ctk.CTk:
    """
    Instantiate and configure the primary application window.

    Applies system-level appearance settings and defines the responsive
    layout grid consisting of a static sidebar (Col 0) and a dynamic
    content area (Col 1).

    Returns:
        ctk.CTk: The configured root application instance.
    """
    # 1. THEME: Apply global visual branding
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    # 2. INSTANTIATION: Create root container
    app = ctk.CTk()

    # 3. CONFIGURATION: Window metadata and constraints
    app.title(f"Transcriptor4AI - v{const.CURRENT_CONFIG_VERSION}")
    app.geometry(DEFAULT_GEOMETRY)
    app.minsize(MIN_WIDTH, MIN_HEIGHT)

    # 4. LAYOUT: Define primary architecture
    # Column 0: Sidebar (Fixed width handled by component)
    # Column 1: Content (Expandable)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    return app