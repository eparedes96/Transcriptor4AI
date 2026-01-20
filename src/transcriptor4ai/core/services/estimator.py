from __future__ import annotations

"""
Cost Estimation Service.

Provides logic to calculate the financial impact of LLM token consumption
based on model-specific pricing. Supports real-time updates via LiteLLM
integration, multi-tier fallback mechanisms, and local cache persistence.
"""

import json
import logging
import os
from typing import Any, Dict, Optional

from transcriptor4ai.domain.constants import AI_MODELS, PRICING_DATA_URL
from transcriptor4ai.infra.fs import get_pricing_cache_path
from transcriptor4ai.infra.network import fetch_pricing_data

logger = logging.getLogger(__name__)


class CostEstimator:
    """
    Orchestrates cost calculations for project transcriptions.

    Implements a 3-tier fallback strategy for pricing:
    1. Live: Fetch from LiteLLM repository.
    2. Cache: Load from local pricing_cache.json.
    3. Default: Fallback to hardcoded AI_MODELS constants.
    """

    def __init__(self, live_pricing: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the estimator.

        Args:
            live_pricing: Optional dictionary with dynamic price overrides.
        """
        self._live_pricing = live_pricing or {}

    def calculate_cost(
            self,
            token_count: int,
            model_name: str,
            precalculated_tokens: Optional[int] = None
    ) -> float:
        """
        Compute the estimated cost in USD for a given token count and model.

        Args:
            token_count: Total tokens processed in current run.
            model_name: Name of the target model.
            precalculated_tokens: If provided (from cache), overrides token_count.

        Returns:
            float: Estimated cost in USD.
        """
        effective_tokens = precalculated_tokens if precalculated_tokens is not None else token_count

        if effective_tokens <= 0:
            return 0.0

        price_info = self._live_pricing.get(model_name) or AI_MODELS.get(model_name)

        if not price_info:
            logger.warning(f"CostEstimator: Model '{model_name}' not found. Cost set to 0.0.")
            return 0.0

        try:
            input_price_1k = float(price_info.get("input_cost_1k", 0.0))
            estimated_cost = (effective_tokens / 1000) * input_price_1k
            return estimated_cost
        except (ValueError, TypeError) as e:
            logger.error(f"CostEstimator: Malformed pricing data for '{model_name}': {e}")
            return 0.0

    def update_live_pricing(self, data: Optional[Dict[str, Any]] = None) -> None:
        """
        Execute the 3-Tier pricing synchronization sequence.

        Tries injected data, then network fetch, then local file cache,
        and finally falls back to hardcoded constants.

        Args:
            data: Optional pre-fetched pricing data (e.g., from a GUI thread).
        """
        # Tier 1: Live Sync (Injected or Fetched)
        raw_data = data if data is not None else fetch_pricing_data(PRICING_DATA_URL)

        if raw_data:
            adapted = self._adapt_litellm_data(raw_data)
            if adapted:
                self._live_pricing = adapted
                self._save_local_cache(adapted)
                logger.info("CostEstimator: Pricing synchronized from LIVE source.")
                return

        # Tier 2: Local Cache Fallback
        cached_data = self._load_local_cache()
        if cached_data:
            self._live_pricing = cached_data
            logger.info("CostEstimator: Pricing loaded from LOCAL CACHE.")
            return

        # Tier 3: Defaults (Already handled by calculate_cost logic)
        logger.warning("CostEstimator: Using hardcoded DEFAULT pricing.")

    def _adapt_litellm_data(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map LiteLLM JSON schema to internal AI_MODELS structure.

        LiteLLM provides 'input_cost_per_token'. We convert to cost per 1k tokens.
        """
        adapted: Dict[str, Any] = {}
        try:
            for model_key, info in raw_data.items():
                if not isinstance(info, dict):
                    continue

                # liteLLM usually provides cost per 1 token
                raw_input_cost = info.get("input_cost_per_token", 0)

                # We normalize it to our 1k format
                adapted[model_key] = {
                    "id": model_key,
                    "input_cost_1k": float(raw_input_cost) * 1000,
                    "provider": info.get("litellm_provider", "UNKNOWN")
                }
            return adapted
        except Exception as e:
            logger.error(f"CostEstimator: Adaptation failed: {e}")
            return {}

    def _load_local_cache(self) -> Optional[Dict[str, Any]]:
        """
        Load pricing from the local filesystem.

        Returns:
            Optional[Dict[str, Any]]: The cached dictionary or None if invalid/missing.
        """
        cache_path = get_pricing_cache_path()
        if not os.path.exists(cache_path):
            return None
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict):
                    return content
                return None
        except Exception as e:
            logger.debug(f"CostEstimator: Failed to read local cache: {e}")
            return None

    def _save_local_cache(self, data: Dict[str, Any]) -> None:
        """Persist pricing data to the local filesystem safely."""
        cache_path = get_pricing_cache_path()
        try:
            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.error(f"CostEstimator: Failed to write local cache: {e}")