from __future__ import annotations

"""
Cost Calculation Application Service.

Implements high-precision financial logic for LLM token consumption. 
Delegates model specifications and pricing discovery to the ModelRegistry, 
ensuring execution metrics are translated into accurate USD estimates.
"""

import logging
from typing import TYPE_CHECKING, Optional

# 1. TYPE CHECKING: External repository reference for dependency injection
if TYPE_CHECKING:
    from transcriptor4ai.domain.ports.model_port import IModelRegistry

logger = logging.getLogger(__name__)


# ==============================================================================
# COST CALCULATOR SERVICE
# ==============================================================================

class CostCalculatorService:
    """
    Service responsible for applying economic formulas to project
    transcription metrics using dynamic registry data.
    """

    def __init__(self, registry: IModelRegistry) -> None:
        """
        Initialize the service with an injected metadata provider.

        Args:
            registry: Discovery service implementation of the IModelRegistry port.
        """
        self._registry = registry

    # --------------------------------------------------------------------------
    # CORE CALCULATION LOGIC
    # --------------------------------------------------------------------------

    def calculate_cost(
            self,
            token_count: int,
            model_name: str,
            precalculated_tokens: Optional[int] = None
    ) -> float:
        """
        Compute the estimated cost in USD for a given token density.

        Args:
            token_count: Current execution tokens (live count).
            model_name: Identifier of the target model in the registry.
            precalculated_tokens: Optional count from cache (overrides live).

        Returns:
            float: Estimated cost in USD. Returns 0.0 on unknown models or errors.
        """
        # 1. ARBITRATION: Select between raw density or precalculated cache hits
        # Cache hits are prioritized to maintain financial consistency between runs.
        effective_tokens = (
            precalculated_tokens if precalculated_tokens is not None else (token_count or 0)
        )

        if effective_tokens <= 0:
            return 0.0

        # 2. LOOKUP: Query the registry for model-specific economic specs
        model_info = self._registry.get_model_info(model_name)

        if not model_info:
            logger.warning(
                f"CostCalculator: Model '{model_name}' not found. Defaulting to 0.0 cost."
            )
            return 0.0

        # 3. MATH: Apply the normalized pricing formula (Price per 1k tokens)
        try:
            input_price_1k = float(model_info.get("input_cost_1k", 0.0))
            estimated_cost = (effective_tokens / 1000) * input_price_1k
            return estimated_cost

        except (ValueError, TypeError) as e:
            logger.error(f"CostCalculator: Numerical failure for model '{model_name}': {e}")
            return 0.0

    # --------------------------------------------------------------------------
    # DATA SYNCHRONIZATION
    # --------------------------------------------------------------------------

    def sync_remote_data(self) -> bool:
        """
        Trigger a remote synchronization cycle via the Registry repository.

        Returns:
            bool: True if live pricing metadata was successfully integrated.
        """
        # Delegating network complexity to the persistence layer
        success = self._registry.sync_remote()

        if success:
            logger.info("CostCalculator: Live financial metadata successfully refreshed.")
        else:
            logger.info("CostCalculator: Using cached or snapshot pricing metadata.")

        return success

    # --------------------------------------------------------------------------
    # TECHNICAL SPECIFICATION HELPERS
    # --------------------------------------------------------------------------

    def get_context_window(self, model_name: str) -> int:
        """
        Retrieve the hardware input limit for the selected model.

        Args:
            model_name: Unique model identifier.

        Returns:
            int: Maximum input tokens. Default safety fallback: 4096.
        """
        info = self._registry.get_model_info(model_name)
        if not info:
            return 4096

        return int(info.get("context_window", 4096))