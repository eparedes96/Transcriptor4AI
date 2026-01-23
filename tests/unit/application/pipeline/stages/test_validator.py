from __future__ import annotations

"""
Unit tests for the Configuration Validator.

Verifies:
1. Type coercion (String to Bool/List).
2. Default value injection.
3. Strict mode validation.
"""

import pytest

from transcriptor4ai.core.pipeline.stages.validator import validate_config


def test_validate_none_returns_defaults() -> None:
    """Passing None should return the full default configuration."""
    cfg, warnings = validate_config(None)

    assert isinstance(cfg, dict)
    # Check key defaults
    assert cfg["process_modules"] is True
    assert cfg["create_unified_file"] is True
    assert cfg["extensions"] == [".py"]

    assert len(warnings) > 0


def test_validate_empty_dict_returns_defaults() -> None:
    """Passing an empty dict should merge with defaults."""
    cfg, warnings = validate_config({})

    assert cfg["output_prefix"] == "transcription"
    assert cfg["generate_tree"] is True
    assert len(warnings) == 0


def test_validate_converts_strings_to_bools() -> None:
    """
    Verify coercion of CLI/GUI string inputs ('true', 'yes', '1')
    to native Booleans.
    """
    raw = {
        "generate_tree": "true",
        "print_tree": "False",
        "show_functions": "1",
        "process_modules": "no",
        "create_unified_file": "yes",
        "create_individual_files": "0"
    }
    cfg, warnings = validate_config(raw, strict=False)

    assert cfg["generate_tree"] is True
    assert cfg["print_tree"] is False
    assert cfg["show_functions"] is True
    assert cfg["process_modules"] is False
    assert cfg["create_unified_file"] is True
    assert cfg["create_individual_files"] is False

    # Should have warnings for each conversion
    assert len(warnings) == 6


def test_validate_normalizes_csv_strings_to_lists() -> None:
    """Verify 'py,txt' strings are converted to lists."""
    raw = {
        "extensions": "py, txt, .js",
        "include_patterns": "test.*"
    }
    cfg, warnings = validate_config(raw, strict=False)

    assert ".py" in cfg["extensions"]
    assert ".txt" in cfg["extensions"]
    assert ".js" in cfg["extensions"]

    assert isinstance(cfg["include_patterns"], list)
    assert cfg["include_patterns"][0] == "test.*"


def test_validate_extensions_adds_dots() -> None:
    """Extensions without dots should have them added automatically."""
    raw = {"extensions": ["py", "java"]}
    cfg, _ = validate_config(raw)

    assert ".py" in cfg["extensions"]
    assert ".java" in cfg["extensions"]


def test_strict_raises_on_bad_type() -> None:
    """
    Strict mode should raise TypeError on mismatch instead of coercing.
    This is useful for internal calls or API usage.
    """
    # 1. Invalid boolean type
    with pytest.raises(TypeError):
        validate_config({"generate_tree": "not_a_bool"}, strict=True)

    # 2. Invalid field value (number instead of bool)
    with pytest.raises(TypeError):
        validate_config({"process_modules": 123}, strict=True)

    # 3. Invalid list container (number instead of list)
    with pytest.raises(TypeError):
        validate_config({"extensions": 123}, strict=True)