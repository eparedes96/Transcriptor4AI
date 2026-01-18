from __future__ import annotations

"""
GUI Entrypoint and Application Lifecycle Orchestrator.

Initializes the CustomTkinter environment, coordinates persistent state loading, 
assembles the visual component hierarchy, and bridges UI events with the 
AppController. Manages asynchronous log polling and background update cycles.
"""

import logging
import queue
import threading
from logging.handlers import QueueHandler
from typing import Dict, Any, Optional

import customtkinter as ctk

from transcriptor4ai.domain import config as cfg
from transcriptor4ai.domain import constants as const
import transcriptor4ai.interface.gui.components.dashboard
import transcriptor4ai.interface.gui.components.logs_console
import transcriptor4ai.interface.gui.components.settings
import transcriptor4ai.interface.gui.components.sidebar
import transcriptor4ai.interface.gui.components.main_window
import transcriptor4ai.interface.gui.controllers.main_controller
import transcriptor4ai.interface.gui.dialogs.feedback_modal
import transcriptor4ai.interface.gui.dialogs.update_modal
from transcriptor4ai.core.services.updater import UpdateManager, UpdateStatus
from transcriptor4ai.infra.logging import (
    configure_logging,
    LoggingConfig,
    get_default_gui_log_path
)
from transcriptor4ai.interface.gui import threads
import tkinter.messagebox as mb

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# MAIN APPLICATION LOOP
# -----------------------------------------------------------------------------

def main() -> None:
    """
    Initialize and launch the Graphical User Interface.

    Executes the six-phase startup sequence: Logging Setup, State Recovery,
    UI Construction, Controller Binding, Task Scheduling, and Loop Entry.
    """
    # -----------------------------------------------------------------------------
    # PHASE 1: DIAGNOSTIC INFRASTRUCTURE SETUP
    # -----------------------------------------------------------------------------
    log_path = get_default_gui_log_path()

    # Configure root logging with rotating file and console handlers via infra
    configure_logging(LoggingConfig(level="INFO", console=True, log_file=log_path))
    logger.info(f"GUI Lifecycle: Initializing v{const.CURRENT_CONFIG_VERSION}")

    # Dedicated queue for UI console (Redundancy check: only one UI handler added to root)
    gui_log_queue: queue.Queue = queue.Queue()
    gui_log_handler = QueueHandler(gui_log_queue)
    gui_log_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(gui_log_handler)

    # -----------------------------------------------------------------------------
    # PHASE 2: PERSISTENT STATE RECOVERY
    # -----------------------------------------------------------------------------
    try:
        app_state = cfg.load_app_state()
        config = cfg.load_config()
        saved_profiles = app_state.get("saved_profiles", {})
        profile_names = sorted(list(saved_profiles.keys()))
    except Exception as e:
        logger.error(f"State Error: Failure during config deserialization: {e}")
        app_state = cfg.get_default_app_state()
        config = cfg.get_default_config()
        profile_names = []

    # -----------------------------------------------------------------------------
    # PHASE 3: VIEW COMPONENT HIERARCHY CONSTRUCTION
    # -----------------------------------------------------------------------------
    app = transcriptor4ai.interface.gui.components.main_window.create_main_window(profile_names, config)

    def show_frame(name: str) -> None:
        """Switch current visible view via grid management."""
        dashboard_frame.grid_forget()
        settings_frame.grid_forget()
        logs_frame.grid_forget()

        sidebar_frame.btn_dashboard.configure(fg_color="transparent")
        sidebar_frame.btn_settings.configure(fg_color="transparent")
        sidebar_frame.btn_logs.configure(fg_color="transparent")

        if name == "dashboard":
            dashboard_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_dashboard.configure(fg_color=("gray75", "gray25"))
        elif name == "settings":
            settings_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_settings.configure(fg_color=("gray75", "gray25"))
        elif name == "logs":
            logs_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
            sidebar_frame.btn_logs.configure(fg_color=("gray75", "gray25"))

    # Instantiate specialized UI modules
    sidebar_frame = transcriptor4ai.interface.gui.components.sidebar.SidebarFrame(app, nav_callback=show_frame)
    sidebar_frame.grid(row=0, column=0, sticky="nsew")

    dashboard_frame = transcriptor4ai.interface.gui.components.dashboard.DashboardFrame(app, config)
    settings_frame = transcriptor4ai.interface.gui.components.settings.SettingsFrame(app, config, profile_names)
    logs_frame = transcriptor4ai.interface.gui.components.logs_console.LogsFrame(app)

    show_frame("dashboard")

    # -----------------------------------------------------------------------------
    # PHASE 4: CONTROLLER INTEGRATION AND EVENT BINDING
    # -----------------------------------------------------------------------------
    controller = transcriptor4ai.interface.gui.controllers.main_controller.AppController(app, config, app_state)
    controller.register_views(dashboard_frame, settings_frame, logs_frame, sidebar_frame)

    # Scrape configuration into widget initial values
    controller.sync_view_from_config()

    # Link execution triggers
    dashboard_frame.btn_process.configure(command=lambda: controller.start_processing(dry_run=False))
    dashboard_frame.btn_simulate.configure(command=lambda: controller.start_processing(dry_run=True))
    dashboard_frame.sw_tree.configure(command=controller.on_tree_toggled)

    # Link I/O directory selectors
    dashboard_frame.btn_browse_in.configure(
        command=lambda: _browse_folder(app, dashboard_frame.entry_input, linked_entry=dashboard_frame.entry_output)
    )
    dashboard_frame.btn_browse_out.configure(
        command=lambda: _browse_folder(app, dashboard_frame.entry_output)
    )

    # Link configuration and profile management events
    settings_frame.btn_load.configure(command=controller.load_profile)
    settings_frame.btn_save.configure(command=controller.save_profile)
    settings_frame.btn_del.configure(command=controller.delete_profile)
    settings_frame.combo_stack.configure(command=controller.on_stack_selected)
    settings_frame.combo_provider.configure(command=controller.on_provider_selected)
    settings_frame.combo_model.configure(command=controller.on_model_selected)
    settings_frame.btn_reset.configure(command=controller.reset_config)

    sidebar_frame.btn_feedback.configure(
        command=lambda: transcriptor4ai.interface.gui.dialogs.feedback_modal.show_feedback_window(app))

    # -----------------------------------------------------------------------------
    # PHASE 5: BACKGROUND POLLING AND TASKS
    # -----------------------------------------------------------------------------
    log_formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S")

    def poll_log_queue() -> None:
        """Continuously flush logs from background queue to the UI console."""
        while not gui_log_queue.empty():
            try:
                record = gui_log_queue.get_nowait()
                msg = log_formatter.format(record)
                logs_frame.append_log(msg)
            except queue.Empty:
                pass
        app.after(100, poll_log_queue)

    def on_update_checked(result: Dict[str, Any], is_manual: bool) -> None:
        """Coordinate the update prompt when a new version is detected."""
        if result.get("has_update"):
            version = result.get("latest_version", "?")

            # Ensure we use the pending binary path from the manager if available
            bin_url = result.get("binary_url", "")
            pending_path = result.get("pending_path", "")

            sidebar_frame.update_badge.configure(
                text=f"Update v{version}",
                state="normal",
                command=lambda: transcriptor4ai.interface.gui.dialogs.update_modal.show_update_prompt_modal(
                    app, version, result.get("changelog", ""),
                    bin_url, pending_path, result.get("download_url", "")
                )
            )
            sidebar_frame.update_badge.grid(row=5, column=0, padx=20, pady=10)

            if is_manual:
                transcriptor4ai.interface.gui.dialogs.update_modal.show_update_prompt_modal(
                    app, version, result.get("changelog", ""),
                    bin_url, pending_path, result.get("download_url", "")
                )
        elif is_manual:
            mb.showinfo("Update Check", "Application is already up to date.")

    # Schedule managed update cycle
    update_manager = UpdateManager()

    def run_ota_cycle(manual: bool = False) -> None:
        """Background wrapper for the silent update manager."""
        try:
            update_manager.run_silent_cycle(const.CURRENT_CONFIG_VERSION)
            info = update_manager.update_info.copy()
            if update_manager.status == UpdateStatus.READY:
                info["pending_path"] = update_manager.pending_path

            app.after(0, lambda: on_update_checked(info, manual))
        except Exception as e:
            logger.error(f"OTA Lifecycle: Background cycle failed: {e}")

    if app_state["app_settings"].get("auto_check_updates"):
        threading.Thread(
            target=run_ota_cycle,
            args=(False,),
            daemon=True
        ).start()


    # -----------------------------------------------------------------------------
    # PHASE 6: LIFECYCLE FINALIZATION
    # -----------------------------------------------------------------------------
    def on_closing() -> None:
        """Persist session state and terminate the process."""
        controller.sync_config_from_view()
        app_state["last_session"] = config
        cfg.save_app_state(app_state)
        app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.after(100, poll_log_queue)

    app.mainloop()


# -----------------------------------------------------------------------------
# PRIVATE UI HELPERS
# -----------------------------------------------------------------------------

def _browse_folder(
        app: ctk.CTk,
        entry_widget: ctk.CTkEntry,
        linked_entry: Optional[ctk.CTkEntry] = None
) -> None:
    """
    Prompt user for directory selection and synchronize related entry widgets.

    Args:
        app: Root application instance.
        entry_widget: Target entry for the primary path update.
        linked_entry: Optional secondary entry to keep in sync.
    """
    path = ctk.filedialog.askdirectory(parent=app, title="Select Directory")
    if path:
        # Update primary input field
        entry_widget.configure(state="normal")
        entry_widget.delete(0, "end")
        entry_widget.insert(0, path)
        entry_widget.configure(state="readonly")

        # Automatically synchronize linked field (usually output follows input)
        if linked_entry:
            linked_entry.configure(state="normal")
            linked_entry.delete(0, "end")
            linked_entry.insert(0, path)
            linked_entry.configure(state="readonly")


if __name__ == "__main__":
    main()