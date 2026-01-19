from __future__ import annotations

"""
Pipeline Execution Results Viewer.

Constructs a summary dialog displayed after successful (or simulated) 
pipeline runs. Provides statistical metrics (tokens, files processed), 
lists generated artifacts, and offers shortcuts for file explorer 
navigation and clipboard synchronization.
"""

import os
from tkinter import messagebox as mb

import customtkinter as ctk

from transcriptor4ai.domain.pipeline_models import PipelineResult
from transcriptor4ai.interface.gui.utils.tk_helpers import open_file_explorer
from transcriptor4ai.utils.i18n import i18n

# -----------------------------------------------------------------------------
# PUBLIC DIALOG API
# -----------------------------------------------------------------------------

def show_results_window(parent: ctk.CTk, result: PipelineResult) -> None:
    """
    Display the results summary modal.

    Dynamically adjusts styling based on dry-run vs physical execution status.

    Args:
        parent: Parent UI window reference.
        result: The PipelineResult object containing execution metadata.
    """
    toplevel = ctk.CTkToplevel(parent)
    toplevel.title(i18n.t("gui.popups.title_result"))
    toplevel.geometry("600x500")
    toplevel.grab_set()

    summary = result.summary or {}
    dry_run = summary.get("dry_run", False)

    # Resolve UI header and color based on execution mode
    if dry_run:
        header_text = i18n.t("gui.results_window.dry_run_header")
        color = "#F0AD4E"
    else:
        header_text = i18n.t("gui.results_window.success_header")
        color = "#2CC985"

    # Header and Status
    ctk.CTkLabel(
        toplevel,
        text=header_text,
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color=color
    ).pack(pady=20)

    # -----------------------------------------------------------------------------
    # STATISTICS GRID
    # -----------------------------------------------------------------------------
    stats_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    stats_frame.pack(pady=10)

    # Files Processed
    proc_val = summary.get('processed', 0)
    proc_txt = f"{i18n.t('gui.results_window.stats_processed')}: {proc_val}"
    ctk.CTkLabel(stats_frame, text=proc_txt).pack()

    # Files Skipped
    skip_val = summary.get('skipped', 0)
    skip_txt = f"{i18n.t('gui.results_window.stats_skipped')}: {skip_val}"
    ctk.CTkLabel(stats_frame, text=skip_txt).pack()

    # Token Count
    token_txt = f"{i18n.t('gui.results_window.stats_tokens')}: {result.token_count:,}"
    ctk.CTkLabel(stats_frame, text=token_txt).pack()

    # -----------------------------------------------------------------------------
    # ARTIFACT LIST SECTION
    # -----------------------------------------------------------------------------
    ctk.CTkLabel(toplevel, text=i18n.t("gui.results_window.files_label")).pack(pady=(20, 5))
    scroll_frame = ctk.CTkScrollableFrame(toplevel, height=150)
    scroll_frame.pack(fill="x", padx=20)

    gen_files = summary.get("generated_files", {})
    unified_path = gen_files.get("unified")

    for key, path in gen_files.items():
        if path:
            name = os.path.basename(path)
            file_entry_txt = f"[{key.upper()}] {name}"
            ctk.CTkLabel(scroll_frame, text=file_entry_txt, anchor="w").pack(fill="x", padx=5)

    # -----------------------------------------------------------------------------
    # ACTION HANDLERS
    # -----------------------------------------------------------------------------

    def _open() -> None:
        """Trigger the host OS file explorer."""
        open_file_explorer(result.final_output_path)

    def _copy() -> None:
        """Synchronize unified context content with the system clipboard."""
        if unified_path and os.path.exists(unified_path):
            try:
                with open(unified_path, "r", encoding="utf-8") as f:
                    parent.clipboard_clear()
                    parent.clipboard_append(f.read())
                info_msg = "Unified content copied to clipboard."
                mb.showinfo(i18n.t("gui.results_window.copied_msg"), info_msg)
            except Exception as e:
                mb.showerror(i18n.t("gui.dialogs.error_title"), str(e))

    # -----------------------------------------------------------------------------
    # ACTION CONTROLS
    # -----------------------------------------------------------------------------
    btn_frame = ctk.CTkFrame(toplevel, fg_color="transparent")
    btn_frame.pack(pady=20, fill="x", padx=20)

    # Open Folder Button
    btn_open = ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_open"),
        command=_open
    )
    btn_open.pack(side="left", expand=True, padx=5)

    # Copy to Clipboard Button
    copy_btn = ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_copy"),
        command=_copy
    )
    copy_btn.pack(side="left", expand=True, padx=5)

    # Validation to prevent copying simulated or non-existent data
    if dry_run or not unified_path:
        copy_btn.configure(state="disabled")

    # Close Dialog Button
    btn_close = ctk.CTkButton(
        btn_frame,
        text=i18n.t("gui.results_window.btn_close"),
        fg_color="transparent",
        border_width=1,
        text_color=("gray10", "#DCE4EE"),
        command=toplevel.destroy
    )
    btn_close.pack(side="left", expand=True, padx=5)