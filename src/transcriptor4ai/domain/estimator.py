from __future__ import annotations

"""
Cost Estimation Service.

Provides logic to calculate the financial impact of LLM token consumption
based on model-specific pricing. Supports real-time updates and fallback 
to domain constants.
"""

import logging
from typing import Any, Dict, Optional

from transcriptor4ai.domain.constants import AI_MODELS

logger = logging.getLogger(__name__)

class CostEstimator:
    """
    Orchestrates cost calculations for project transcriptions.

    Uses a hybrid approach: attempts to use live pricing data if available,
    otherwise falls back to static definitions in AI_MODELS.
    """

    def __init__(self, live_pricing: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the estimator.

        Args:
            live_pricing: Optional dictionary with dynamic price overrides.
        """
        self._live_pricing = live_pricing or {}

    def calculate_cost(self, token_count: int, model_name: str) -> float:
        """
        Compute the estimated cost in USD for a given token count and model.

        Calculates input cost only, as the transcription serves as the
        prompt context for the AI.

        Args:
            token_count: Total number of tokens processed.
            model_name: Name of the target model (must exist in constants or live data).

        Returns:
            float: Estimated cost in USD. Returns 0.0 if the model is not found.
        """
        if token_count <= 0:
            return 0.0

        # 1. Try to get price from live data first
        price_info = self._live_pricing.get(model_name)

        # 2. Fallback to static AI_MODELS constant
        if not price_info:
            price_info = AI_MODELS.get(model_name)

        if not price_info:
            logger.warning(
                f"CostEstimator: Model '{model_name}' not found in pricing data. "
                "Returning 0.0."
            )
            return 0.0

        try:
            # We focus on input_cost as the tool generates the prompt context
            input_price_1k = float(price_info.get("input_cost_1k", 0.0))
            estimated_cost = (token_count / 1000) * input_price_1k

            logger.debug(
                f"Cost calculated for {model_name}: {token_count} tokens = "
                f"${estimated_cost:.4f}"
            )
            return estimated_cost

        except (ValueError, TypeError) as e:
            logger.error(f"CostEstimator: Malformed pricing data for '{model_name}': {e}")
            return 0.0

    def update_live_pricing(self, new_pricing: Dict[str, Any]) -> None:
        """
        Update the internal override table with fresh network data.

        Args:
            new_pricing: Freshly fetched pricing dictionary.
        """
        self._live_pricing = new_pricing
        logger.info("CostEstimator: Live pricing data updated.")