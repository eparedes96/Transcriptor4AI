from __future__ import annotations

"""
GUI Entrypoint and Application Lifecycle Orchestrator.

Initializes the CustomTkinter environment, coordinates persistent state loading
via dependency injection, assembles the visual component hierarchy, and bridges
UI events with the AppController.
"""

import logging
import os
import queue
import threading
from logging.handlers import QueueHandler
from typing import List, Optional

import customtkinter as ctk

# Domain Entities & Config
from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.shared import constants as const

# Infrastructure Implementation (Concrete Adapters)
from transcriptor4ai.infrastructure.logging import LoggingConfig, configure_logging, get_default_gui_log_path
from transcriptor4ai.infrastructure.persistence.json_config_repo import JsonConfigRepository
from transcriptor4ai.infrastructure.persistence.model_registry_repo import ModelRegistryRepository
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter
from transcriptor4ai.infrastructure.system.user_context_adapter import UserContextAdapter
from transcriptor4ai.infrastructure.network.github_release_client import GithubReleaseClient

# Application Services
from transcriptor4ai.application.services.update_service import UpdateManager

# Interface Components & Controllers
from transcriptor4ai.interface.gui.common import async_workers
from transcriptor4ai.interface.gui.components.dashboard import DashboardFrame
from transcriptor4ai.interface.gui.components.logs_console import LogsFrame
from transcriptor4ai.interface.gui.components.main_window import create_main_window
from transcriptor4ai.interface.gui.components.settings import SettingsFrame
from transcriptor4ai.interface.gui.components.sidebar import SidebarFrame
from transcriptor4ai.interface.gui.controllers.coordinator import AppController
from transcriptor4ai.interface.gui.controllers.update_controller import UpdateController
from transcriptor4ai.interface.gui.dialogs.feedback_modal import show_feedback_window

logger = logging.getLogger(__name__)


# ==============================================================================
# MAIN APPLICATION ENTRYPOINT
# ==============================================================================

def main() -> None:
    """
    Initialize and launch the Graphical User Interface.

    Executes the six-phase startup sequence:
    1. Diagnostic Bootstrap (Logging)
    2. Infrastructure Instantiation (Adapters)
    3. State Recovery (Persistence)
    4. View Hierarchy Assembly (Tkinter)
    5. Controller Injection (DIP)
    6. Background Task Scheduling (Threads)
    """

    # --- PHASE 1: DIAGNOSTIC INFRASTRUCTURE ---
    log_path: str = get_default_gui_log_path()

    # Configure root logging with rotating file and console handlers
    configure_logging(LoggingConfig(level="INFO", console=True, log_file=log_path))
    logger.info(f"GUI Lifecycle: Initializing v{const.CURRENT_CONFIG_VERSION}")

    # Queue for asynchronous UI log console updates
    gui_log_queue: queue.Queue[logging.LogRecord] = queue.Queue()
    gui_log_handler = QueueHandler(gui_log_queue)
    gui_log_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(gui_log_handler)

    # --- PHASE 2: INFRASTRUCTURE INSTANTIATION ---
    # Create concrete adapters to be injected into the application core
    fs_adapter = FileSystemAdapter()
    config_repo = JsonConfigRepository(fs_adapter)
    cache_repo = SqliteCacheRepository(fs_adapter)
    model_registry = ModelRegistryRepository(fs_adapter)
    user_adapter = UserContextAdapter()
    network_client = GithubReleaseClient()

    # --- PHASE 3: PERSISTENT STATE RECOVERY ---
    try:
        app_state = config_repo.load_app_state()
        config = config_repo.load_config()
        saved_profiles = app_state.get("saved_profiles", {})
        profile_names: List[str] = sorted(list(saved_profiles.keys()))
    except Exception as e:
        logger.error(f"State Error: Failure during config deserialization: {e}")
        # Fallback to domain defaults if persistence fails
        cwd = os.getcwd()
        app_state = domain_cfg.get_default_app_state(cwd)
        config = domain_cfg.get_default_config(cwd)
        profile_names = []

    # --- PHASE 4: VIEW COMPONENT HIERARCHY ---
    app: ctk.CTk = create_main_window()

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
    sidebar_frame = SidebarFrame(app, nav_callback=show_frame)
    sidebar_frame.grid(row=0, column=0, sticky="nsew")

    dashboard_frame = DashboardFrame(app, config)
    settings_frame = SettingsFrame(app, config, profile_names)
    logs_frame = LogsFrame(app)

    # Set default view
    show_frame("dashboard")

    # --- PHASE 5: CONTROLLER INTEGRATION (DIP) ---
    # Inject infrastructure adapters into the Main Controller
    controller = AppController(
        app=app,
        config=config,
        app_state=app_state,
        fs=fs_adapter,
        cache=cache_repo,
        config_repo=config_repo,
        registry=model_registry,
        user_context=user_adapter
    )
    controller.register_views(dashboard_frame, settings_frame, logs_frame, sidebar_frame)

    # Initialize Update Management Controller (OTA) with injected dependencies
    update_manager = UpdateManager(network_client, fs_adapter)
    ota_controller = UpdateController(app, sidebar_frame, update_manager)

    # Scrape configuration into widget initial values
    controller.sync_view_from_config()

    # --- EVENT BINDING ---
    dashboard_frame.btn_process.configure(
        command=lambda: controller.start_processing(dry_run=False)
    )
    dashboard_frame.btn_simulate.configure(
        command=lambda: controller.start_processing(dry_run=True)
    )
    dashboard_frame.sw_tree.configure(command=controller.on_tree_toggled)

    dashboard_frame.btn_browse_in.configure(
        command=lambda: _browse_folder(
            app,
            dashboard_frame.entry_input,
            linked_entry=dashboard_frame.entry_output
        )
    )
    dashboard_frame.btn_browse_out.configure(
        command=lambda: _browse_folder(app, dashboard_frame.entry_output)
    )

    # Link Settings Triggers
    settings_frame.btn_load.configure(command=controller.load_profile)
    settings_frame.btn_save.configure(command=controller.save_profile)
    settings_frame.btn_del.configure(command=controller.delete_profile)

    # Bind Cache Management
    settings_frame.btn_purge.configure(command=controller.purge_cache)

    # Link dynamic dropdown selections to the controller
    settings_frame.combo_stack.configure(command=controller.on_stack_selected)
    settings_frame.combo_provider.configure(command=controller.on_provider_selected)
    settings_frame.combo_model.configure(command=controller.on_model_selected)
    settings_frame.btn_reset.configure(command=controller.reset_config)

    # Link Sidebar Triggers
    sidebar_frame.btn_feedback.configure(command=lambda: show_feedback_window(app))

    # --- PHASE 6: BACKGROUND POLLING & TASKS ---
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

    # Automatic update check scheduling
    if app_state.get("app_settings", {}).get("auto_check_updates"):
        threading.Thread(
            target=ota_controller.run_silent_cycle,
            kwargs={"manual": False},
            daemon=True
        ).start()

    # Dynamic Pricing and Model Discovery Synchronization
    threading.Thread(
        target=async_workers.run_pricing_sync_task,
        args=(controller.cost_estimator, lambda data: app.after(
            0, lambda: controller.on_pricing_updated(data)
        )),
        daemon=True
    ).start()

    # --- PHASE 7: LIFECYCLE FINALIZATION ---
    def on_closing() -> None:
        """Persist session state and terminate the process."""
        try:
            controller.sync_config_from_view()
            app_state["last_session"] = config
            config_repo.save_app_state(app_state)
            logger.info("Application state persisted successfully during shutdown.")
        except Exception as e:
            logger.error(f"Shutdown: Failed to save state: {e}")
        finally:
            app.destroy()

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.after(100, poll_log_queue)

    app.mainloop()


# ==============================================================================
# PRIVATE UI HELPERS
# ==============================================================================

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
    path: str = ctk.filedialog.askdirectory(parent=app, title="Select Directory")
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