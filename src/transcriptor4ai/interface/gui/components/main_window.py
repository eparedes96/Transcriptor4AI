from __future__ import annotations

"""
Main Application Window Factory.

Initializes the root CustomTkinter application window, configures 
global theme attributes, and establishes the primary structural 
grid for navigation and content rendering.
"""

from typing import Any, Dict, List

import customtkinter as ctk

from transcriptor4ai.domain import constants as const

# -----------------------------------------------------------------------------
# ROOT WINDOW CONSTRUCTION
# -----------------------------------------------------------------------------

def create_main_window(
        profile_names: List[str],
        config: Dict[str, Any]
) -> ctk.CTk:
    """
    Instantiate and configure the primary application window.

    Applies system-level appearance settings and defines the responsive
    layout grid consisting of a static sidebar and a dynamic content area.

    Args:
        profile_names: List of available user profile identifiers.
        config: Initial session configuration state.

    Returns:
        ctk.CTk: The configured root application instance.
    """
    # Global visual branding
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()

    # Window metadata and constraints
    app.title(f"Transcriptor4AI - v{const.CURRENT_CONFIG_VERSION}")
    app.geometry("1000x700")

    # Define primary architecture: Column 0 (Sidebar), Column 1 (Content)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    return app