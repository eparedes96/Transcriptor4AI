from __future__ import annotations

"""
Cost Estimation Service.

Provides high-precision financial calculations for LLM token consumption.
Delegates model technical specifications and pricing discovery to the 
ModelRegistry, focusing exclusively on applying economic formulas to 
execution metrics.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from transcriptor4ai.core.services.registry import ModelRegistry

logger = logging.getLogger(__name__)


class CostEstimator:
    """
    Service responsible for calculating the estimated financial impact
    of project transcriptions based on dynamic registry data.
    """

    def __init__(self, registry: ModelRegistry) -> None:
        """
        Initialize the estimator with a model metadata provider.

        Args:
            registry: The discovery service acting as the source of truth.
        """
        self._registry = registry

    def calculate_cost(
            self,
            token_count: int,
            model_name: str,
            precalculated_tokens: Optional[int] = None
    ) -> float:
        """
        Compute the estimated cost in USD for a given token density.

        Queries the registry for the specific model's price per 1k tokens.
        Supports cache-hit overrides to ensure financial consistency.

        Args:
            token_count: Current execution tokens.
            model_name: Identifier of the target model in the registry.
            precalculated_tokens: Optional count from cache to prioritize.

        Returns:
            float: Estimated cost in USD. Returns 0.0 if model is unknown.
        """
        effective_tokens = (
            precalculated_tokens if precalculated_tokens is not None else token_count
        )

        if effective_tokens <= 0:
            return 0.0

        model_info = self._registry.get_model_info(model_name)

        if not model_info:
            logger.warning(
                f"CostEstimator: Model '{model_name}' not found in registry. Cost set to 0.0."
            )
            return 0.0

        try:
            # Registry ensures input_cost_1k is normalized to 1000 tokens
            input_price_1k = float(model_info.get("input_cost_1k", 0.0))
            estimated_cost = (effective_tokens / 1000) * input_price_1k
            return estimated_cost
        except (ValueError, TypeError) as e:
            logger.error(f"CostEstimator: Numerical failure for model '{model_name}': {e}")
            return 0.0

    def update_live_pricing(self) -> None:
        """
        Trigger a remote synchronization cycle in the registry.

        This method maintains compatibility with the interface controller
        while delegating the complex discovery logic to the Registry service.
        """
        success = self._registry.sync_remote()
        if success:
            logger.info("CostEstimator: Financial metadata refreshed via Registry.")
        else:
            logger.warning("CostEstimator: Registry sync failed. Using last known data.")

    def get_context_limit(self, model_name: str) -> int:
        """
        Retrieve the maximum context window for a given model.

        Used by controllers to perform pre-flight technical validations.

        Args:
            model_name: Identifier of the target model.

        Returns:
            int: Maximum input tokens allowed. Defaults to 4096.
        """
        info = self._registry.get_model_info(model_name)
        if not info:
            return 4096
        return int(info.get("context_window", 4096))