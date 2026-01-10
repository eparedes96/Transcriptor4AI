from __future__ import annotations

import pytest
from transcriptor4ai.validate_config import validate_config


# -----------------------------------------------------------------------------
# 1. Base Structure & Defaults
# -----------------------------------------------------------------------------

def test_validate_none_returns_defaults():
    """Passing None should return the default configuration."""
    cfg, warnings = validate_config(None)

    assert isinstance(cfg, dict)

    assert cfg["process_modules"] is True
    assert cfg["process_tests"] is True
    assert cfg["create_unified_file"] is True

    assert cfg["extensions"] == [".py"]
    assert len(warnings) > 0


def test_validate_empty_dict_returns_defaults():
    """Passing an empty dict should fill in all default values."""
    cfg, warnings = validate_config({})

    assert cfg["output_prefix"] == "transcription"
    assert cfg["generate_tree"] is True
    assert cfg["create_individual_files"] is True
    assert len(warnings) == 0


# -----------------------------------------------------------------------------
# 2. Type Correction (Non-Strict Mode)
# -----------------------------------------------------------------------------

def test_validate_converts_strings_to_bools():
    """Common scenario: CLI/GUI passing 'true'/'false' strings."""
    raw = {
        "generate_tree": "true",
        "print_tree": "False",
        "show_functions": "1",
        "process_modules": "no",
        "create_unified_file": "yes",
        "create_individual_files": "0"
    }
    cfg, warnings = validate_config(raw, strict=False)

    # Assertions
    assert cfg["generate_tree"] is True
    assert cfg["print_tree"] is False
    assert cfg["show_functions"] is True
    assert cfg["process_modules"] is False
    assert cfg["create_unified_file"] is True
    assert cfg["create_individual_files"] is False

    assert len(warnings) == 6


def test_validate_normalizes_csv_strings_to_lists():
    """Common scenario: 'py,txt' from CLI args."""
    raw = {
        "extensions": "py, txt, .js",
        "include_patterns": "test.*"
    }
    cfg, warnings = validate_config(raw, strict=False)

    # Logic adds dot if missing
    assert ".py" in cfg["extensions"]
    assert ".txt" in cfg["extensions"]
    assert ".js" in cfg["extensions"]
    assert isinstance(cfg["include_patterns"], list)
    assert cfg["include_patterns"][0] == "test.*"


# -----------------------------------------------------------------------------
# 3. Logic Validation
# -----------------------------------------------------------------------------

def test_validate_extensions_adds_dots():
    """Extensions without dots should have them added."""
    raw = {"extensions": ["py", "java"]}
    cfg, _ = validate_config(raw)

    assert ".py" in cfg["extensions"]
    assert ".java" in cfg["extensions"]


# -----------------------------------------------------------------------------
# 4. Strict Mode (Failures)
# -----------------------------------------------------------------------------

def test_strict_raises_on_bad_type():
    """Strict mode should raise TypeError on mismatch."""
    raw = {"generate_tree": "not_a_bool"}

    with pytest.raises(TypeError):
        validate_config(raw, strict=True)

    raw2 = {"process_modules": "maybe"}
    with pytest.raises(TypeError):
        validate_config(raw2, strict=True)