from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Dict, Optional

from transcriptor4ai.domain import constants as const
from transcriptor4ai.utils.i18n import i18n

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController

logger = logging.getLogger(__name__)


class PricingController:
    """
    Manages financial logic, model discovery, and provider filtering.
    """

    def __init__(self, main_controller: AppController):
        self.main = main_controller

    def sync_remote_data(self, data: Optional[Dict[str, Any]]) -> None:
        """Handle remote discovery completion and refresh UI components."""
        # Update core services hosted in Main
        self.main.cost_estimator.update_live_pricing()

        dashboard = self.main.dashboard_view
        if dashboard and hasattr(dashboard, "set_pricing_status"):
            is_live: bool = self.main.registry._is_live_synced
            dashboard.set_pricing_status(is_live=is_live)

        self.main.sync_view_from_config()
        logger.info("UI: Model and pricing discovery synced and views refreshed.")

    def handle_provider_change(self, provider: str) -> None:
        """Update the model selection list when the provider changes."""
        self.update_model_list(provider)

        # Get the new default model selected by the update_model_list logic
        new_model: str = self.main.settings_view.combo_model.get()
        self.main.config["target_model"] = new_model

        self.handle_model_change(new_model)

    def handle_model_change(self, model_name: str) -> None:
        """Update session state silently and log selection."""
        self.main.config["target_model"] = model_name
        logger.info(f"UI: Model context switched to '{model_name}'.")

    def update_model_list(
            self,
            provider: str,
            preserve_selection: Optional[str] = None
    ) -> None:
        """Filter the model list based on discovered data."""
        discovered = self.main.registry.get_available_models()

        # Logic to filter models by provider
        models = sorted([
            m_id for m_id, info in discovered.items()
            if info.get("provider") == provider
        ])

        if not models:
            models = ["-- No Models --"]

        # Update UI directly via Main reference
        combo = self.main.settings_view.combo_model
        combo.configure(values=models)

        if preserve_selection and preserve_selection in models:
            combo.set(preserve_selection)
        else:
            combo.set(models[0])
            self.main.config["target_model"] = models[0]