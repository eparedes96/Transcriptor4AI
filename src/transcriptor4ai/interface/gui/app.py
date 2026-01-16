from __future__ import annotations

"""
Main Entry Point for the Graphical User Interface.

This module orchestrates the application lifecycle using CustomTkinter:
1. Initialization (Logging, State Load).
2. UI Construction (assembling Layouts).
3. Logic Integration (linking the AppController).
4. Main Event Loop Management.
"""

import logging
import queue
import threading
from logging.handlers import QueueHandler
from typing import Dict, Any, Optional

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.infra.logging import (
    configure_logging,
    LoggingConfig,
    get_default_gui_log_path
)
from transcriptor4ai.interface.gui import layouts, handlers, threads

logger = logging.getLogger(__name__)


def main() -> None:
    """
    Main GUI Application loop (V2.0 Architecture).
    """
    # -------------------------------------------------------------------------
    # 1. System Initialization
    # -------------------------------------------------------------------------
    log_path = get_default_gui_log_path()
    # Configure root logger with thread-safe queue for file/console
    configure_logging(LoggingConfig(level="INFO", console=True, log_file=log_path))
    logger.info(f"GUI V2.0 Starting - Version {cfg.CURRENT_CONFIG_VERSION}")

    # Setup a specific queue for the GUI Log Console widget
    gui_log_queue: queue.Queue = queue.Queue()
    gui_log_handler = QueueHandler(gui_log_queue)
    gui_log_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(gui_log_handler)

    # -------------------------------------------------------------------------
    # 2. State Loading
    # -------------------------------------------------------------------------
    try:
        app_state = cfg.load_app_state()
        config = cfg.load_config()
        saved_profiles = app_state.get("saved_profiles", {})
        profile_names = sorted(list(saved_profiles.keys()))
    except Exception as e:
        logger.error(f"State load failed: {e}")
        app_state = cfg.get_default_app_state()
        config = cfg.get_default_config()
        profile_names = []

    # -------------------------------------------------------------------------
    # 3. View Construction (Wireframe)
    # -------------------------------------------------------------------------
    app = layouts.create_main_window(profile_names, config)

    # Define Navigation Logic
    def show_frame(name: str) -> None:
        """Switch visible content frame."""
        # Hide all
        dashboard_frame.grid_forget()
        settings_frame.grid_forget()
        logs_frame.grid_forget()

        # Update Sidebar Buttons visual state
        sidebar_frame.btn_dashboard.configure(fg_color="transparent")
        sidebar_frame.btn_settings.configure(fg_color="transparent")
        sidebar_frame.btn_logs.configure(fg_color="transparent")

        # Show selected
        if name == "dashboard":
            dashboard_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_dashboard.configure(fg_color=("gray75", "gray25"))
        elif name == "settings":
            settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_settings.configure(fg_color=("gray75", "gray25"))
        elif name == "logs":
            logs_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_logs.configure(fg_color=("gray75", "gray25"))

    # Instantiate Frames
    sidebar_frame = layouts.SidebarFrame(app, nav_callback=show_frame)
    sidebar_frame.grid(row=0, column=0, sticky="nsew")

    dashboard_frame = layouts.DashboardFrame(app, config)
    settings_frame = layouts.SettingsFrame(app, config, profile_names)
    logs_frame = layouts.LogsFrame(app)

    # Default View
    show_frame("dashboard")

    # -------------------------------------------------------------------------
    # 4. Logic Integration (Controller)
    # -------------------------------------------------------------------------
    controller = handlers.AppController(app, config, app_state)
    controller.register_views(dashboard_frame, settings_frame, logs_frame, sidebar_frame)

    # Sync initial state to widgets
    controller.sync_view_from_config()

    # Link View Events to Controller Actions
    dashboard_frame.btn_process.configure(command=lambda: controller.start_processing(dry_run=False))
    dashboard_frame.btn_simulate.configure(command=lambda: controller.start_processing(dry_run=True))

    # Link dynamic Tree Switch
    dashboard_frame.sw_tree.configure(command=controller.on_tree_toggled)

    # Update Input
    dashboard_frame.btn_browse_in.configure(
        command=lambda: _browse_folder(
            app,
            dashboard_frame.entry_input,
            linked_entry=dashboard_frame.entry_output
        )
    )
    # Update Output
    dashboard_frame.btn_browse_out.configure(
        command=lambda: _browse_folder(app, dashboard_frame.entry_output)
    )

    settings_frame.btn_load.configure(command=controller.load_profile)
    settings_frame.btn_save.configure(command=controller.save_profile)
    settings_frame.btn_del.configure(command=controller.delete_profile)
    settings_frame.combo_stack.configure(command=controller.on_stack_selected)
    settings_frame.combo_provider.configure(command=controller.on_provider_selected)
    settings_frame.combo_model.configure(command=controller.on_model_selected)

    settings_frame.btn_reset.configure(command=controller.reset_config)
    sidebar_frame.btn_feedback.configure(command=lambda: handlers.show_feedback_window(app))

    # -------------------------------------------------------------------------
    # 5. Background Tasks & Polling
    # -------------------------------------------------------------------------

    # Log Polling (Updates UI Log Console safely from main thread)
    log_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")

    def poll_log_queue() -> None:
        """Fetch logs from background queue and update UI."""
        while not gui_log_queue.empty():
            try:
                record = gui_log_queue.get_nowait()
                msg = log_formatter.format(record)
                logs_frame.append_log(msg)
            except queue.Empty:
                pass
        app.after(100, poll_log_queue)

    # Auto-Update Check
    def on_update_checked(result: Dict[str, Any], is_manual: bool) -> None:
        """Callback when update check finishes."""
        if result.get("has_update"):
            version = result.get("latest_version", "?")
            logger.info(f"Update available: {version}")
            sidebar_frame.update_badge.configure(text=f"Update v{version}", state="normal")
            sidebar_frame.update_badge.grid(row=5, column=0, padx=20, pady=10)

            # If manual check, show prompt immediately
            if is_manual:
                handlers.show_update_prompt_modal(
                    app, version, result.get("changelog", ""),
                    result.get("binary_url", ""), "", result.get("download_url", "")
                )
        elif is_manual:
            handlers.mb.showinfo("Update Check", "App is up to date.")

    if app_state["app_settings"].get("auto_check_updates"):
        threading.Thread(
            target=threads.check_updates_task,
            args=(on_update_checked, False),
            daemon=True
        ).start()

    # -------------------------------------------------------------------------
    # 6. Lifecycle Management
    # -------------------------------------------------------------------------
    def on_closing() -> None:
        """Handle app exit."""
        # Save last session state
        controller.sync_config_from_view()
        app_state["last_session"] = config
        cfg.save_app_state(app_state)

        # Shutdown
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)

    # Start Polling
    app.after(100, poll_log_queue)

    # Launch
    app.mainloop()


def _browse_folder(
        app: ctk.CTk,
        entry_widget: ctk.CTkEntry,
        linked_entry: Optional[ctk.CTkEntry] = None
) -> None:
    """Helper for folder selection dialog."""
    path = ctk.filedialog.askdirectory(parent=app, title="Select Directory")
    if path:
        # Update primary entry
        entry_widget.configure(state="normal")
        entry_widget.delete(0, "end")
        entry_widget.insert(0, path)
        entry_widget.configure(state="readonly")

        # Automatically sync linked entry to the same path
        if linked_entry:
            linked_entry.configure(state="normal")
            linked_entry.delete(0, "end")
            linked_entry.insert(0, path)
            linked_entry.configure(state="readonly")


if __name__ == "__main__":
    main()