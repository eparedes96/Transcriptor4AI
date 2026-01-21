from __future__ import annotations

"""
Model Discovery and Registry Service.

Acts as the central authority for AI model metadata. Orchestrates the 
discovery lifecycle by merging build-time snapshots with live remote 
data from LiteLLM. Implements canonical filtering to prioritize base 
models over infrastructure-specific variants (Azure, Bedrock, etc.).
"""

import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional

from transcriptor4ai.domain import constants as const
from transcriptor4ai.infra import network
from transcriptor4ai.infra.fs import get_user_data_dir

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Service responsible for the discovery, normalization, and filtering
    of AI model technical and economic specifications.
    """

    def __init__(self) -> None:
        """Initialize the registry with thread-safe storage and default state."""
        self._models: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._is_live_synced = False

        # Path to local cache in user data directory
        self._cache_path = os.path.join(
            get_user_data_dir(),
            const.LOCAL_PRICING_FILENAME
        )

    def get_available_models(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve the curated catalog of discovered models.

        Returns:
            Dict[str, Dict[str, Any]]: Map of Model ID to normalized metadata.
        """
        with self._lock:
            if not self._models:
                self._load_initial_data()
            return self._models.copy()

    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch normalized metadata for a specific model.

        Args:
            model_id: The unique identifier for the model.

        Returns:
            Optional[Dict[str, Any]]: Model details or None if not found.
        """
        return self.get_available_models().get(model_id)

    def sync_remote(self) -> bool:
        """
        Orchestrate a non-blocking update from the remote authority.

        Returns:
            bool: True if live data was successfully integrated.
        """
        logger.debug("Registry: Starting remote discovery cycle...")
        raw_data = network.fetch_external_model_data(const.MODEL_DATA_URL)

        if not raw_data:
            return False

        normalized = self._normalize_and_filter(raw_data)
        if not normalized:
            return False

        with self._lock:
            self._models.update(normalized)
            self._is_live_synced = True
            self._save_to_cache(normalized)

        logger.info(f"Registry: Live discovery complete. {len(normalized)} models curated.")
        return True

    def _load_initial_data(self) -> None:
        """
        Perform the bootstrap sequence: Cache -> Bundled Snapshot.
        """
        # Tier 1: Try local session cache (Pricing Cache)
        if os.path.exists(self._cache_path):
            try:
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if isinstance(cached_data, dict):
                        self._models = cached_data
                        logger.debug("Registry: Initialized from local session cache.")
                        return
            except Exception as e:
                logger.warning(f"Registry: Failed to load cache: {e}")

        # Tier 2: Try bundled snapshot (Build-time assets)
        bundled_path = self._get_bundled_path()
        if os.path.exists(bundled_path):
            try:
                with open(bundled_path, "r", encoding="utf-8") as f:
                    raw_bundled = json.load(f)
                    self._models = self._normalize_and_filter(raw_bundled)
                    logger.info("Registry: Initialized from bundled snapshot.")
                    return
            except Exception as e:
                logger.error(f"Registry: Critical failure loading bundled snapshot: {e}")

        logger.warning("Registry: Starting with an empty catalog (Offline/No Snapshot).")

    def _normalize_and_filter(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        The Gatekeeper: Transforms and curates the massive LiteLLM JSON.

        Implements:
        1. Mode Filtering (Text only).
        2. Canonical Heuristic (Filter Azure/Bedrock if base exists).
        3. Unit Conversion (Cost per 1k).
        """
        curated: Dict[str, Dict[str, Any]] = {}

        # 1. First Pass: Internal Normalization
        for model_id, info in raw_data.items():
            if not isinstance(info, dict) or model_id == "sample_spec":
                continue

            # Filtering: Only text-based models
            mode = info.get("mode", "").lower()
            if mode not in ("chat", "completion"):
                continue

            # Adaptive context window resolution
            context = info.get("max_input_tokens") or info.get("max_tokens") or 4096

            # Price normalization (to 1k tokens)
            in_cost = float(info.get("input_cost_per_token", 0.0)) * 1000
            out_cost = float(info.get("output_cost_per_token", 0.0)) * 1000

            curated[model_id] = {
                "id": model_id,
                "provider": info.get("litellm_provider", "unknown").upper(),
                "input_cost_1k": in_cost,
                "output_cost_1k": out_cost,
                "context_window": int(context),
            }

        # 2. Second Pass: Canonical Cleanup (Infrastructure De-duplication)
        return self._filter_canonical_models(curated)

    def _filter_canonical_models(self, models: Dict[str, Any]) -> Dict[str, Any]:
        """
        Filter out regional or infrastructure duplicates.

        Example: If 'gpt-4o' and 'azure/gpt-4o' exist, keep only 'gpt-4o'.
        """
        infrastructure_providers = ("AZURE", "BEDROCK", "VERTEX_AI", "SAGEMAKER")
        clean_catalog: Dict[str, Any] = {}

        # Group by base name (part after slash)
        for mid, data in models.items():
            base_name = mid.split("/")[-1] if "/" in mid else mid

            # If we don't have this base name yet, or the new one is NOT infrastructure
            if base_name not in clean_catalog:
                clean_catalog[base_name] = data
            else:
                current_is_infra = clean_catalog[base_name]["provider"] in infrastructure_providers
                new_is_infra = data["provider"] in infrastructure_providers

                # Favor non-infrastructure (original) providers
                if current_is_infra and not new_is_infra:
                    clean_catalog[base_name] = data

        return clean_catalog

    def _get_bundled_path(self) -> str:
        """Resolve the absolute path to the bundled resource."""
        import sys
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Fallback for development (src/transcriptor4ai/assets/)
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_path = os.path.join(base_path, "assets")

        return os.path.join(base_path, const.BUNDLED_DATA_FILENAME)

    def _save_to_cache(self, data: Dict[str, Any]) -> None:
        """Persist curated data to the local pricing cache."""
        try:
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            logger.debug(f"Registry: Failed to write cache: {e}")