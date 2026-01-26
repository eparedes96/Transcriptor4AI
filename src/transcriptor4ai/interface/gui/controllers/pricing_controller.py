from __future__ import annotations

"""
GUI Pricing and Model Controller.

Mediates between the dynamic AI Model Registry and the user interface. 
Handles model discovery synchronization, provider-based filtering, and 
updates the execution state to ensure accurate cost estimation.
"""

import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

# Standard logger initialization
logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from transcriptor4ai.interface.gui.controllers.main_controller import AppController


# ==============================================================================
# PRICING CONTROLLER
# ==============================================================================

class PricingController:
    """
    Controller responsible for financial UI logic and model selection.
    """

    def __init__(self, main_controller: AppController) -> None:
        """
        Initialize the controller with a reference to the main hub.
        """
        self.main = main_controller

    # ==========================================================================
    # DATA SYNCHRONIZATION
    # ==========================================================================

    def sync_remote_data(self, data: Optional[Dict[str, Any]]) -> None:
        """
        Handle the completion of the remote model discovery task.

        Args:
            data: Raw data from the network (ignored as the service handles persistence).
        """
        # 1. PROCESS: Trigger service-level synchronization
        # The CostCalculatorService orchestrates the Registry and fallbacks
        success = self.main.cost_estimator.sync_remote_data()

        # 2. UI UPDATE: Reflect network status in the Dashboard
        dashboard = self.main.dashboard_view
        if dashboard and hasattr(dashboard, "set_pricing_status"):
            # Note: Success implies live data; failure defaults to cached
            dashboard.set_pricing_status(is_live=success)

        # 3. REFRESH: Re-populate views to reflect new models/prices
        self.main.sync_view_from_config()

        logger.info("PricingController: Remote discovery cycle processed and views updated.")

    # ==========================================================================
    # UI EVENT HANDLERS
    # ==========================================================================

    def handle_provider_change(self, provider: str) -> None:
        """
        Update the model selection list when the user selects a new provider.

        Args:
            provider: Canonical name of the AI provider (e.g., 'OPENAI').
        """
        # 1. FILTER: Update the dependent model list
        self.update_model_list(provider)

        # 2. SYNC: Capture the newly selected default model into session config
        new_model: str = self.main.settings_view.combo_model.get()
        self.main.config["target_model"] = new_model

        # 3. LOG: Notify internal state of the switch
        self.handle_model_change(new_model)

    def handle_model_change(self, model_name: str) -> None:
        """
        Update the transient session state when a specific model is selected.
        """
        self.main.config["target_model"] = model_name
        logger.info(f"PricingController: Target model switched to '{model_name}'.")

    # ==========================================================================
    # LIST MANAGEMENT
    # ==========================================================================

    def update_model_list(
            self,
            provider: str,
            preserve_selection: Optional[str] = None
    ) -> None:
        """
        Populate the model ComboBox based on discovered registry data.

        Args:
            provider: The source provider to filter by.
            preserve_selection: Optional model ID to maintain if available.
        """
        # 1. RETRIEVE: Get current catalog from the Model Registry port
        discovered = self.main.registry.get_available_models()

        # 2. FILTER: Extract models belonging to the target provider
        models: List[str] = sorted([
            m_id for m_id, info in discovered.items()
            if info.get("provider") == provider
        ])

        # Safety fallback for UI stability
        if not models:
            models = ["-- No Models --"]

        # 3. WIDGET UPDATE: Inject values into the view
        combo = self.main.settings_view.combo_model
        combo.configure(values=models)

        # 4. ARBITRATION: Resolve selection state
        if preserve_selection and preserve_selection in models:
            # Maintain existing selection if it exists in the new provider list
            combo.set(preserve_selection)
        else:
            # Default to the first available model in the new list
            default_m = models[0]
            combo.set(default_m)
            self.main.config["target_model"] = default_m