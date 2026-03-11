from __future__ import annotations

# ==============================================================================
# TEST GROUP: CONFIGURATION VALIDATOR STAGE
# ==============================================================================
import pytest

from transcriptor4ai.application.pipeline.stages.validator import validate_config


@pytest.mark.unit
def test_validate_none_returns_defaults():
    """
    Ensures that passing None as configuration results in a complete
    dictionary of default values and a warning.
    """
    # 2. ACT
    cfg, warnings = validate_config(None)

    # 3. ASSERT
    assert isinstance(cfg, dict)
    assert cfg["process_modules"] is True
    assert cfg["extensions"] == [".py"]
    assert any("Invalid config type" in w for w in warnings)


@pytest.mark.unit
@pytest.mark.parametrize("raw_value, expected_bool", [
    ("true", True),
    ("yes", True),
    ("1", True),
    ("false", False),
    ("no", False),
    ("0", False),
])
def test_validate_coerces_strings_to_bools(raw_value, expected_bool):
    """
    Verifies that various string representations of truthiness coming
    from CLI/GUI are correctly coerced into Python booleans.
    """
    # 1. ARRANGE
    raw_input = {"generate_tree": raw_value}

    # 2. ACT
    cfg, _ = validate_config(raw_input)

    # 3. ASSERT
    assert cfg["generate_tree"] is expected_bool


@pytest.mark.unit
def test_validate_normalizes_extensions_with_dots():
    """
    Extensions provided without a leading dot should be automatically
    fixed to match the internal filtering expectations.
    """
    # 1. ARRANGE
    raw_input = {"extensions": ["py", "js", ".ts"]}

    # 2. ACT
    cfg, _ = validate_config(raw_input)

    # 3. ASSERT
    assert cfg["extensions"] == [".py", ".js", ".ts"]


@pytest.mark.unit
def test_validate_parses_csv_strings_into_lists():
    """
    Inputs coming from a single text field (CSV style) should be
    split into clean, trimmed lists.
    """
    # 1. ARRANGE
    raw_input = {"include_patterns": "src/.*, tests/.*"}

    # 2. ACT
    cfg, _ = validate_config(raw_input)

    # 3. ASSERT
    assert cfg["include_patterns"] == ["src/.*", "tests/.*"]


@pytest.mark.unit
def test_validate_enforces_integrity_modules_and_depth():
    """
    Business Rule: If 'process_modules' is disabled, the 'processing_depth'
    must be forced to 'tree_only' regardless of user input.
    """
    # 1. ARRANGE
    raw_input = {
        "process_modules": False,
        "processing_depth": "full"
    }

    # 2. ACT
    cfg, _ = validate_config(raw_input)

    # 3. ASSERT
    assert cfg["processing_depth"] == "tree_only"


@pytest.mark.unit
def test_validate_strict_mode_raises_type_error():
    """
    In strict mode, actual type mismatches (like list instead of bool)
    should raise a TypeError.
    """
    # 1. ARRANGE: Enviamos una lista, que NO es (bool, int, str)
    bad_input = {"minify_output": ["invalid_type"]}

    # 2. ACT & 3. ASSERT
    with pytest.raises(TypeError, match="Cannot coerce"):
        validate_config(bad_input, strict=True)


@pytest.mark.unit
def test_validate_preserves_unrecognized_fields():
    """
    Ensures that additional fields not defined in the standard schema
    are preserved (useful for future-proofing or temporary flags).
    """
    # 1. ARRANGE
    raw_input = {"experimental_feature": True}

    # 2. ACT
    cfg, _ = validate_config(raw_input)

    # 3. ASSERT
    assert cfg["experimental_feature"] is True