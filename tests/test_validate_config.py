# tests/test_validate_config.py
import pytest
from transcriptor4ai.validate_config import validate_config


# -----------------------------------------------------------------------------
# 1. Base Structure & Defaults
# -----------------------------------------------------------------------------

def test_validate_none_returns_defaults():
    """Passing None should return the default configuration."""
    cfg, warnings = validate_config(None)

    assert isinstance(cfg, dict)
    assert cfg["processing_mode"] == "all"
    assert cfg["extensiones"] == [".py"]
    # Should produce a warning about invalid type
    assert len(warnings) > 0


def test_validate_empty_dict_returns_defaults():
    """Passing an empty dict should fill in all default values."""
    cfg, warnings = validate_config({})

    assert cfg["output_prefix"] == "transcription"
    assert cfg["generate_tree"] is False
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
        "show_classes": "0"
    }
    cfg, warnings = validate_config(raw, strict=False)

    assert cfg["generate_tree"] is True
    assert cfg["print_tree"] is False
    assert cfg["show_functions"] is True
    assert cfg["show_classes"] is False
    assert len(warnings) == 4  # One warning per conversion


def test_validate_normalizes_csv_strings_to_lists():
    """Common scenario: 'py,txt' from CLI args."""
    raw = {
        "extensiones": "py, txt, .js",
        "include_patterns": "test.*"
    }
    cfg, warnings = validate_config(raw, strict=False)

    # Logic adds dot if missing
    assert ".py" in cfg["extensiones"]
    assert ".txt" in cfg["extensiones"]
    assert ".js" in cfg["extensiones"]
    assert isinstance(cfg["include_patterns"], list)
    assert cfg["include_patterns"][0] == "test.*"


# -----------------------------------------------------------------------------
# 3. Enum & Logic Validation
# -----------------------------------------------------------------------------

def test_validate_modo_fallback():
    """Invalid mode should fallback to 'all'."""
    raw = {"processing_mode": "invalid_mode"}
    cfg, warnings = validate_config(raw)

    assert cfg["processing_mode"] == "all"
    assert any("fallback" in w for w in warnings)


def test_validate_extensions_adds_dots():
    """Extensions without dots should have them added."""
    raw = {"extensiones": ["py", "java"]}
    cfg, _ = validate_config(raw)

    assert ".py" in cfg["extensiones"]
    assert ".java" in cfg["extensiones"]


# -----------------------------------------------------------------------------
# 4. Strict Mode (Failures)
# -----------------------------------------------------------------------------

def test_strict_raises_on_bad_type():
    """Strict mode should raise TypeError on mismatch."""
    raw = {"generate_tree": "not_a_bool"}

    with pytest.raises(TypeError):
        validate_config(raw, strict=True)


def test_strict_raises_on_bad_enum():
    """Strict mode should raise ValueError on invalid mode."""
    raw = {"processing_mode": "super_mode"}

    with pytest.raises(ValueError):
        validate_config(raw, strict=True)