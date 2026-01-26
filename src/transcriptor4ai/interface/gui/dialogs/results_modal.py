from __future__ import annotations

"""
Pipeline Execution Results Viewer.

Constructs a summary dialog displayed after successful or simulated pipeline 
runs. Provides statistical metrics (tokens, files processed), lists generated 
artifacts, and offers shortcuts for file explorer navigation and clipboard 
synchronization of the final AI context.
"""

import logging
import os
from tkinter import messagebox as mb
from typing import Final

import customtkinter as ctk

from transcriptor4ai.domain.entities.pipeline_results import PipelineResult
from transcriptor4ai.infrastructure.system.os_file_system import open_file_explorer
from transcriptor4ai.shared.i18n import i18n

# Global logger initialization
logger = logging.getLogger(__name__)

# ==============================================================================
# UI STYLE CONSTANTS
# ==============================================================================
COLOR_SUCCESS: Final[str] = "#2CC985"
COLOR_SIMULATION: Final[str] = "#F0AD4E"
COLOR_SECONDARY: Final[str] = "#DCE4EE"


# ==============================================================================
# PUBLIC DIALOG API
# ==============================================================================

def show_results_window(parent: ctk.CTk, result: PipelineResult) -> None:
    """
    Display the results summary modal.

    Args:
        parent: Parent UI window reference for modal anchoring.
        result: Inmutable result object containing execution metadata.
    """
    # 1. INITIALIZATION: Setup modal properties
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.popups.title_result"))
    toplevel.geometry("600x550")
    toplevel.grab_set()  # Prevent interaction with the main window

    summary = result.summary or {}
    is_dry_run = bool(summary.get("dry_run", False))

    # ==========================================================================
    # UI CONSTRUCTION: HEADER
    # ==========================================================================

    # Resolve status visual cues based on execution mode
    header_text = (
        i18n.t("gui.results_window.dry_run_header") if is_dry_run
        else i18n.t("gui.results_window.success_header")
    )
    status_color = COLOR_SIMULATION if is_dry_run else COLOR_SUCCESS

    ctk.CTkLabel(
        toplevel,
        text=header_text,
        font=ctk.CTkFont(size=20, weight="bold"),
        text_color=status_color
    ).pack(pady=(25, 15))

    # ==========================================================================
    # UI CONSTRUCTION: STATISTICS
    # ==========================================================================
    stats_container = ctk.CTkFrame(toplevel, fg_color="transparent")
    stats_container.pack(pady=10)

    # 1. METRIC: Files successfully processed
    proc_val = summary.get('processed', 0)
    ctk.CTkLabel(
        stats_container,
        text=f"{i18n.t('gui.results_window.stats_processed')}: {proc_val}",
        font=ctk.CTkFont(size=13)
    ).pack()

    # 2. METRIC: Files skipped by filters or cache hit
    skip_val = summary.get('skipped', 0)
    ctk.CTkLabel(
        stats_container,
        text=f"{i18n.t('gui.results_window.stats_skipped')}: {skip_val}",
        font=ctk.CTkFont(size=13)
    ).pack()

    # 3. METRIC: Final token density
    ctk.CTkLabel(
        stats_container,
        text=f"{i18n.t('gui.results_window.stats_tokens')}: {result.token_count:,}",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(pady=(5, 0))

    # ==========================================================================
    # UI CONSTRUCTION: ARTIFACT EXPLORER
    # ==========================================================================
    ctk.CTkLabel(
        toplevel,
        text=i18n.t("gui.results_window.files_label"),
        font=ctk.CTkFont(weight="bold")
    ).pack(pady=(20, 5))

    scroll_frame = ctk.CTkScrollableFrame(toplevel, height=180, corner_radius=10)
    scroll_frame.pack(fill="x", padx=30)

    generated_map = summary.get("generated_files", {})
    unified_path = generated_map.get("unified")

    # Populate list with generated file names and types
    for category, path in generated_map.items():
        if path and isinstance(path, str) and os.path.exists(path):
            file_name = os.path.basename(path)
            display_text = f"[{category.upper()}] {file_name}"
            ctk.CTkLabel(scroll_frame, text=display_text, anchor="w").pack(fill="x", padx=10, pady=2)

    # ==========================================================================
    # INTERNAL ACTION LOGIC
    # ==========================================================================

    def _on_open_folder() -> None:
        """Invoke the system explorer at the output destination."""
        try:
            open_file_explorer(result.final_output_path)
        except Exception as e:
            logger.error(f"ResultsModal: Failed to open explorer -> {e}")
            mb.showerror(i18n.t("gui.dialogs.error_title"), str(e))

    def _on_copy_content() -> None:
        """Read the unified context and synchronize with system clipboard."""
        # Verification: Prevent clipboard errors if the file was moved/deleted
        if not unified_path or not os.path.exists(unified_path):
            return

        try:
            # PROCESS: Read context using standard encoding resilience
            with open(unified_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                parent.clipboard_clear()
                parent.clipboard_append(content)

            mb.showinfo(
                i18n.t("gui.results_window.copied_msg"),
                "Unified context copied to clipboard."
            )
        except OSError as e:
            logger.error(f"ResultsModal: Clipboard sync failure -> {e}")
            mb.showerror(i18n.t("gui.dialogs.error_title"), f"Failed to read output:\n{e}")

    # ==========================================================================
    # ACTION BAR
    # ==========================================================================
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(side="bottom", fill="x", padx=30, pady=25)

    # Trigger: OS Folder exploration
    ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_open"),
        command=_on_open_folder
    ).pack(side="left", expand=True, padx=(0, 5))

    # Trigger: Quick AI Ingestion (Copy)
    copy_btn = ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_copy"),
        command=_on_copy_content
    )
    copy_btn.pack(side="left", expand=True, padx=5)

    # Validation: Disable copy for dry runs (no physical file exists)
    if is_dry_run or not unified_path:
        copy_btn.configure(state="disabled", fg_color="gray40")

    # Trigger: Modal Disposal
    ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_close"),
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", COLOR_SECONDARY),
        command=toplevel.destroy
    ).pack(side="left", expand=True, padx=(5, 0))