from __future__ import annotations

from typing import List, Dict, Any

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg


def create_main_window(
        profile_names: List[str],
        config: Dict[str, Any]
) -> ctk.CTk:
    """
    Factory to create the root CustomTkinter application window.
    It prepares the layout but does NOT start the loop.

    Args:
        profile_names: List of available profiles.
        config: Initial configuration dict.

    Returns:
        ctk.CTk: The configured root window object (with Frames attached).
    """
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")

    app = ctk.CTk()

    app.title(f"Transcriptor4AI - v{cfg.CURRENT_CONFIG_VERSION}")
    app.geometry("1000x700")

    # Configure Grid Layout (1 Sidebar + 1 Content)
    app.grid_columnconfigure(1, weight=1)
    app.grid_rowconfigure(0, weight=1)

    return app
