import json
import re
from pathlib import Path
from typing import Dict, Set, Any

import pytest


# ==============================================================================
# TEST GROUP: I18N PARITY AND COMPLIANCE
# ==============================================================================

def flatten_dict(d: Dict[str, Any], parent_key: str = '') -> Dict[str, Any]:
    """
    Utility to transform a nested dictionary into a flat map of dot-notation keys.
    Example: {"a": {"b": "val"}} -> {"a.b": "val"}
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key).items())
        else:
            items.append((new_key, v))
    return dict(items)


def extract_placeholders(text: str) -> Set[str]:
    """Extracts all patterns like {variable_name} from a string."""
    if not isinstance(text, str):
        return set()
    return set(re.findall(r"\{(\w+)\}", text))


@pytest.fixture
def locales_path() -> Path:
    """Resolves the path to the translation files in the source tree."""
    return Path(__file__).parent.parent.parent.parent / "src" / "transcriptor4ai" / "interface" / "locales"


@pytest.fixture
def load_locale(locales_path):
    """Factory to load and parse a specific locale JSON."""

    def _load(lang: str) -> Dict[str, Any]:
        file_path = locales_path / f"{lang}.json"
        if not file_path.exists():
            pytest.fail(f"Locale file missing: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    return _load


@pytest.mark.unit
def test_locales_should_have_identical_keys(load_locale):
    """
    Ensures that English and Spanish locale files have the exact same
    set of keys, preventing missing translations in the UI.
    """
    # 1. ARRANGE: Load and flatten both dictionaries
    en_data = flatten_dict(load_locale("en"))
    es_data = flatten_dict(load_locale("es"))

    en_keys = set(en_data.keys())
    es_keys = set(es_data.keys())

    # 2. ACT & 3. ASSERT: Compare key sets
    missing_in_es = en_keys - es_keys
    missing_in_en = es_keys - en_keys

    assert not missing_in_es, f"Keys present in EN but missing in ES: {missing_in_es}"
    assert not missing_in_en, f"Keys present in ES but missing in EN: {missing_in_en}"


@pytest.mark.unit
def test_locales_should_have_matching_placeholders(load_locale):
    """
    Validates that if a translation string contains a placeholder (e.g. {path}),
    its counterpart in the other language has the same placeholder name.
    """
    # 1. ARRANGE: Flatten both to compare value by value
    en_flat = flatten_dict(load_locale("en"))
    es_flat = flatten_dict(load_locale("es"))

    # 2. ACT & 3. ASSERT
    for key, en_value in en_flat.items():
        if key not in es_flat:
            continue  # Covered by parity test above

        es_value = es_flat[key]

        en_placeholders = extract_placeholders(en_value)
        es_placeholders = extract_placeholders(es_value)

        # Ensure both languages expect the same variables for .format()
        assert en_placeholders == es_placeholders, (
            f"Placeholder mismatch at key '{key}': "
            f"EN has {en_placeholders}, but ES has {es_placeholders}"
        )


@pytest.mark.unit
def test_locales_structure_type_integrity(load_locale):
    """
    Ensures that if a key represents a category (dict) in one language,
    it is also a category in the other, not a terminal string.
    """
    # 1. ARRANGE
    en_data = load_locale("en")
    es_data = load_locale("es")

    def verify_recursive_structure(en_node, es_node, path="root"):
        # 2. ACT & 3. ASSERT
        assert type(en_node) is type(es_node), f"Type mismatch at '{path}': {type(en_node)} vs {type(es_node)}"

        if isinstance(en_node, dict):
            for key in en_node:
                if key in es_node:
                    verify_recursive_structure(en_node[key], es_node[key], f"{path}.{key}")

    verify_recursive_structure(en_data, es_data)