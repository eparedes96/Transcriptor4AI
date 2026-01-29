from __future__ import annotations

# ==============================================================================
# TEST GROUP: MODEL CURATOR SERVICE
# ==============================================================================

import pytest
from typing import Any, Dict

from transcriptor4ai.domain.services.model_curator import curate_model_list


@pytest.fixture
def raw_litellm_data() -> Dict[str, Any]:
    """
    Simulates a slice of the LiteLLM master JSON including noise and duplicates.
    """
    return {
        "gpt-4o": {
            "mode": "chat",
            "input_cost_per_token": 0.000005,
            "output_cost_per_token": 0.000015,
            "litellm_provider": "openai",
            "max_input_tokens": 128000
        },
        "azure/gpt-4o": {
            "mode": "chat",
            "input_cost_per_token": 0.000005,
            "output_cost_per_token": 0.000015,
            "litellm_provider": "azure",
            "max_tokens": 128000
        },
        "whisper-1": {
            "mode": "audio_transcription",  # Should be filtered out
            "input_cost_per_token": 0.1
        },
        "dall-e-3": {
            "mode": "image_generation",  # Should be filtered out
            "input_cost_per_token": 0.04
        },
        "sample_spec": {"info": "metadata"}  # Internal LiteLLM key, should be ignored
    }


def test_curate_filters_non_text_models(raw_litellm_data):
    """
    Ensures that only chat and completion models are preserved in the catalog.
    """
    # 2. ACT
    curated = curate_model_list(raw_litellm_data)

    # 3. ASSERT
    # Audio and image models must be discarded
    assert "whisper-1" not in curated
    assert "dall-e-3" not in curated
    assert "sample_spec" not in curated
    assert "gpt-4o" in curated


def test_curate_price_normalization_math(raw_litellm_data):
    """
    Validates that cost per token is accurately converted to cost per 1k tokens.
    Formula: input_cost_per_token * 1000
    """
    # 2. ACT
    curated = curate_model_list(raw_litellm_data)

    # 3. ASSERT
    model_data = curated["gpt-4o"]
    # 0.000005 * 1000 = 0.005
    assert model_data["input_cost_1k"] == pytest.approx(0.005)
    assert model_data["output_cost_1k"] == pytest.approx(0.015)


def test_curate_context_window_fallback_logic():
    """
    Verifies that the curator correctly identifies the context window
    using 'max_input_tokens' first, then 'max_tokens'.
    """
    # 1. ARRANGE
    data = {
        "model-a": {"mode": "chat", "max_input_tokens": 100, "litellm_provider": "openai"},
        "model-b": {"mode": "chat", "max_tokens": 50, "litellm_provider": "openai"}
    }

    # 2. ACT
    curated = curate_model_list(data)

    # 3. ASSERT
    assert curated["model-a"]["context_window"] == 100
    assert curated["model-b"]["context_window"] == 50


def test_canonical_filter_prioritizes_direct_provider(raw_litellm_data):
    """
    Verify that when a model is available via direct provider and infra mirror (Azure/AWS),
    the direct provider version is kept to reduce UI clutter.
    """
    # 2. ACT
    curated = curate_model_list(raw_litellm_data)

    # 3. ASSERT
    # 'azure/gpt-4o' and 'gpt-4o' share the same base name.
    # 'gpt-4o' (OpenAI) should prevail over 'azure/gpt-4o' (Infrastructure).
    assert "gpt-4o" in curated
    assert curated["gpt-4o"]["provider"] == "OPENAI"

    # Ensure the infrastructure-prefixed key is gone
    assert "azure/gpt-4o" not in curated


def test_curate_handles_malformed_data():
    """
    Ensures the curator is resilient against malformed numeric strings
    or missing price keys in the source JSON.
    """
    # 1. ARRANGE
    bad_data = {
        "broken-model": {
            "mode": "chat",
            "input_cost_per_token": "not-a-number",  # Malformed
            "litellm_provider": "openai"
        }
    }

    # 2. ACT
    curated = curate_model_list(bad_data)

    # 3. ASSERT
    # The malformed entry should be skipped, not crash the app
    assert "broken-model" not in curated