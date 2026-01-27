from __future__ import annotations

"""
Model Curation and Normalization Service.

Provides deterministic domain logic for processing raw model metadata. 
Responsible for filtering text-based models, normalizing financial metrics, 
and resolving provider canonicality to ensure a consistent model catalog.
"""

import logging
from typing import Any, Dict, Final

# Standardized logger for domain services
logger = logging.getLogger(__name__)


# ==============================================================================
# POLICIES AND MAPPINGS
# ==============================================================================

# Standardizes heterogeneous provider names into canonical application identifiers
_PROVIDER_MAPPING: Final[Dict[str, str]] = {
    "AZURE": "AZURE",
    "AZURE_AI": "AZURE",
    "AZURE_TEXT": "AZURE",
    "BEDROCK": "AWS (BEDROCK)",
    "BEDROCK_CONVERSE": "AWS (BEDROCK)",
    "SAGEMAKER": "AWS (SAGEMAKER)",
    "VERTEX_AI": "GOOGLE (VERTEX)",
    "GEMINI": "GOOGLE",
    "PALM": "GOOGLE",
    "OPENROUTER": "OPENROUTER",
    "TOGETHER_AI": "TOGETHER AI",
    "ANYSCALE": "ANYSCALE",
    "FIREWORKS_AI": "FIREWORKS AI",
    "DEEPINFRA": "DEEPINFRA",
    "FRIENDLIAI": "FRIENDLI AI",
    "CLOUDFLARE": "CLOUDFLARE",
    "DATABRICKS": "DATABRICKS",
    "GITHUB_COPILOT": "GITHUB",
    "TEXT-COMPLETION-OPENAI": "OPENAI",
}

# Keywords used to identify cloud infrastructure resellers for canonical filtering
_INFRA_KEYWORDS: Final[tuple[str, ...]] = ("AZURE", "BEDROCK", "VERTEX", "SAGEMAKER")


# ==============================================================================
# PUBLIC API: MODEL CURATION
# ==============================================================================

def curate_model_list(raw_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Transform and filter raw external data into a sanitized application catalog.

    Processes LiteLLM schema by extracting text-generation models and
    applying the adapter pattern to normalize pricing and identifiers.

    Args:
        raw_data: Unfiltered dictionary from the remote pricing authority.

    Returns:
        Dict[str, Dict[str, Any]]: A clean map of Model ID to curated metadata.
    """
    curated: Dict[str, Dict[str, Any]] = {}

    # 1. VALIDATION: Iterate and sanitize raw definitions
    for model_id, info in raw_data.items():
        if not isinstance(info, dict) or model_id == "sample_spec":
            continue

        # 2. FILTER: Limit scope to text-based models (Chat/Completion)
        mode = info.get("mode", "").lower()
        if mode not in ("chat", "completion"):
            continue

        # 3. TRANSFORMATION: Adapt external metrics to internal schema
        try:
            # Normalize costs: LiteLLM uses unit price, we use 1k token price
            in_cost = float(info.get("input_cost_per_token", 0.0)) * 1000
            out_cost = float(info.get("output_cost_per_token", 0.0)) * 1000

            raw_prov = str(info.get("litellm_provider", "unknown")).upper()
            canonical_provider = _PROVIDER_MAPPING.get(raw_prov, raw_prov)

            # Resolve context window with tiered fallback logic
            context = info.get("max_input_tokens") or info.get("max_tokens") or 4096

            curated[model_id] = {
                "id": model_id,
                "provider": canonical_provider,
                "input_cost_1k": in_cost,
                "output_cost_1k": out_cost,
                "context_window": int(context),
            }

        except (ValueError, TypeError) as e:
            logger.debug(f"Curator: Skipping malformed model entry '{model_id}': {e}")
            continue

    # 4. RESOLUTION: Apply canonical filters to remove redundant infrastructure entries
    return _apply_canonical_filter(curated)


# ==============================================================================
# PRIVATE HELPERS: DEDUPLICATION
# ==============================================================================

def _apply_canonical_filter(models: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify and prioritize direct provider models over regional cloud mirrors.

    Prevents UI clutter by ensuring that if a model (e.g. 'gpt-4o') is available
    directly and via a cloud reseller (e.g. Azure), only one representation exists
    unless they are functionally distinct.
    """
    clean_catalog: Dict[str, Any] = {}

    for mid, data in models.items():
        # Extract base name (e.g., 'openai/gpt-4' -> 'gpt-4')
        base_name = mid.split("/")[-1] if "/" in mid else mid

        if base_name not in clean_catalog:
            clean_catalog[base_name] = data
        else:
            # LOGIC: If a conflict exists, prioritize direct provider over cloud infra
            current_provider = clean_catalog[base_name]["provider"]
            new_provider = data["provider"]

            current_is_infra = any(k in current_provider for k in _INFRA_KEYWORDS)
            new_is_infra = any(k in new_provider for k in _INFRA_KEYWORDS)

            # If current stored is infra-based and new is direct, override
            if current_is_infra and not new_is_infra:
                clean_catalog[base_name] = data
                logger.debug(f"Curator: Prioritizing direct provider for '{base_name}'")

    return clean_catalog