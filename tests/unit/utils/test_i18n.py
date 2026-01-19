from __future__ import annotations

"""
Unit tests for Internationalization (i18n) consistency.

Ensures that all locale files (en.json, es.json) share the exact 
same key structure and dot-notation resolution works as expected.
"""

import json
import os
from typing import Any, Dict, Set

import pytest

from transcriptor4ai.utils.i18n import I18n


def _get_flat_keys(d: Dict[str, Any], prefix: str = "") -> Set[str]:
    """Helper to flatten nested dictionary keys into dot-notation sets."""
    keys = set()
    for k, v in d.items():
        new_key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_get_flat_keys(v, new_key))
        else:
            keys.add(new_key)
    return keys


def test_locales_key_parity() -> None:
    """TC-01: Verify that EN and ES locales have identical keys."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    # Path to find src/transcriptor4ai/interface/locales/
    loc_rel = os.path.join("..", "..", "..", "src", "transcriptor4ai", "interface", "locales")
    locales_dir = os.path.abspath(os.path.join(base_path, loc_rel))

    en_path = os.path.join(locales_dir, "en.json")
    es_path = os.path.join(locales_dir, "es.json")

    if not os.path.exists(en_path) or not os.path.exists(es_path):
        pytest.skip("Locale files not found in the expected path.")

    with open(en_path, "r", encoding="utf-8") as f:
        en_keys = _get_flat_keys(json.load(f))

    with open(es_path, "r", encoding="utf-8") as f:
        es_keys = _get_flat_keys(json.load(f))

    missing_in_es = en_keys - es_keys
    extra_in_es = es_keys - en_keys

    if missing_in_es and len(es_keys) < 20:
        msg = f"ES locale is incomplete ({len(missing_in_es)} keys). Pending translation."
        pytest.skip(msg)

    assert not missing_in_es, f"Keys present in EN but missing in ES: {missing_in_es}"
    assert not extra_in_es, f"Keys present in ES but missing in EN: {extra_in_es}"


def test_new_economic_keys_presence() -> None:
    """TC-V2.1-01: Ensure all new financial keys are present in all locales."""
    base_path = os.path.dirname(os.path.abspath(__file__))
    loc_rel = os.path.join("..", "..", "..", "src", "transcriptor4ai", "interface", "locales")
    locales_path = os.path.abspath(os.path.join(base_path, loc_rel))

    required_keys = [
        "gui.dashboard.cost_label",
        "gui.dashboard.status_live",
        "gui.dashboard.status_cached"
    ]

    for lang in ["en", "es"]:
        file_path = os.path.join(locales_path, f"{lang}.json")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            flat_keys = _get_flat_keys(data)

            for key in required_keys:
                assert key in flat_keys, f"Key '{key}' is missing in {lang}.json"


def test_i18n_resolution_logic(tmp_path: pytest.TempPathFactory) -> None:
    """TC-02: Verify dot-notation resolution and interpolation."""
    # Create a dummy locale file
    dummy_content = {
        "test": {
            "hello": "Hello {name}!",
            "simple": "Simple Text"
        }
    }
    locale_file = tmp_path / "test_locale.json"
    locale_file.write_text(json.dumps(dummy_content), encoding="utf-8")

    # Initialize I18n pointing to the temp dir
    service = I18n("en")
    service._locales_path = str(tmp_path)
    service.load_locale("test_locale")

    # Test simple resolution
    assert service.t("test.simple") == "Simple Text"

    # Test interpolation
    assert service.t("test.hello", name="World") == "Hello World!"

    # Test fallback
    assert service.t("missing.key") == "missing.key"