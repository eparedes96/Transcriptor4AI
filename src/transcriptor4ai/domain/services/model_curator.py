from __future__ import annotations

"""
Model Curation Service.

Provides pure domain logic for filtering and normalizing raw model data 
from external providers. Ensures only compatible text models are 
exposed to the application.
"""

from typing import Any, Dict, Final

# ==============================================================================
# CONSTANTS & POLICIES
# ==============================================================================

_PROVIDER_MAPPING: Final[Dict[str, str]] = {
    "AZURE": "AZURE",
    "AZURE_AI": "AZURE",
    "BEDROCK": "AWS (BEDROCK)",
    "GEMINI": "GOOGLE",
    "VERTEX_AI": "GOOGLE (VERTEX)",
    # ... resto del mapeo que estaba en el repo
}

_INFRA_KEYWORDS: Final[tuple[str, ...]] = ("AZURE", "BEDROCK", "VERTEX", "SAGEMAKER")


# ==============================================================================
# PUBLIC API
# ==============================================================================

def curate_model_list(raw_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Transform and filter raw external data into a clean application catalog.
    """
    curated: Dict[str, Dict[str, Any]] = {}

    # 1. VALIDATION & NORMALIZATION
    for model_id, info in raw_data.items():
        if not isinstance(info, dict) or model_id == "sample_spec":
            continue

        # Solo modelos de texto
        mode = info.get("mode", "").lower()
        if mode not in ("chat", "completion"):
            continue

        # Normalización económica (coste por 1k tokens)
        in_cost = float(info.get("input_cost_per_token", 0.0)) * 1000
        out_cost = float(info.get("output_cost_per_token", 0.0)) * 1000

        raw_prov = info.get("litellm_provider", "unknown").upper()

        curated[model_id] = {
            "id": model_id,
            "provider": _PROVIDER_MAPPING.get(raw_prov, raw_prov),
            "input_cost_1k": in_cost,
            "output_cost_1k": out_cost,
            "context_window": int(info.get("max_input_tokens") or 4096),
        }

    # 2. FILTERING: Eliminar duplicados de infraestructura
    return _apply_canonical_filter(curated)


def _apply_canonical_filter(models: Dict[str, Any]) -> Dict[str, Any]:
    """Identify and prioritize base models over regional infra duplicates."""
    clean_catalog: Dict[str, Any] = {}

    for mid, data in models.items():
        base_name = mid.split("/")[-1] if "/" in mid else mid

        if base_name not in clean_catalog:
            clean_catalog[base_name] = data
        else:
            # Priorizar proveedor directo sobre infraestructura de nube
            current_prov = clean_catalog[base_name]["provider"]
            new_prov = data["provider"]

            is_curr_infra = any(k in current_prov for k in _INFRA_KEYWORDS)
            is_new_infra = any(k in new_prov for k in _INFRA_KEYWORDS)

            if is_curr_infra and not is_new_infra:
                clean_catalog[base_name] = data

    return clean_catalog