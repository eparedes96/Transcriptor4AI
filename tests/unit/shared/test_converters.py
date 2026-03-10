import pytest
from transcriptor4ai.shared import converters


# ==============================================================================
# TEST GROUP: STRING CONVERSION (to_str)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_val, fallback, expected", [
    ("hello", "default", "hello"),
    ("  trimmed  ", "default", "trimmed"),
    ("", "default", "default"),
    (None, "fallback_val", "fallback_val"),
    (123, "default", "123"),
])
def test_to_str_should_sanitize_and_handle_fallbacks(input_val, fallback, expected):
    """Verifies that strings are trimmed and nulls/empties trigger fallbacks."""
    # 1. ARRANGE & 2. ACT
    result = converters.to_str(input_val, fallback)

    # 3. ASSERT
    assert result == expected


# ==============================================================================
# TEST GROUP: BOOLEAN COERCION (scrub_bool)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_val, expected", [
    (True, True),
    (False, False),
    ("true", True),
    ("FALSE", False),
    ("yes", True),
    ("n", False),
    ("1", True),
    ("0", False),
    (1, True),
    (0, False),
    ("on", True),
    ("off", False),
    ("sí", True),  # Spanish support check
])
def test_scrub_bool_should_coerce_truthy_and_falsy_values(input_val, expected):
    """Ensures various representations of booleans are correctly translated."""
    # 1. ARRANGE & 2. ACT
    result = converters.scrub_bool(input_val)

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
def test_scrub_bool_strict_mode_should_raise_type_error():
    """Validates that strict mode prevents coercion of complex types."""
    # 1. ARRANGE
    bad_input = ["not", "a", "bool"]

    # 2. ACT & 3. ASSERT
    with pytest.raises(TypeError, match="Cannot coerce list"):
        converters.scrub_bool(bad_input, strict=True)


# ==============================================================================
# TEST GROUP: LIST PARSING (to_list_str)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_val, expected", [
    ("py,js, ts", ["py", "js", "ts"]),
    ([".py", ".ts"], [".py", ".ts"]),
    ("  ", []),
    (None, []),
    (["", "valid"], ["valid"]),
])
def test_to_list_str_should_parse_csv_and_filter_empty_items(input_val, expected):
    """Verifies CSV parsing and cleaning of string lists."""
    # 1. ARRANGE & 2. ACT
    result = converters.to_list_str(input_val)

    # 3. ASSERT
    assert result == expected


@pytest.mark.unit
def test_to_list_str_should_return_fallback_on_invalid_input():
    """Ensures fallback list is used when input is unparseable."""
    # 1. ARRANGE
    fallback = ["default.py"]

    # 2. ACT
    result = converters.to_list_str(None, fallback=fallback)

    # 3. ASSERT
    assert result == fallback
    assert result is not fallback  # Should be a copy


# ==============================================================================
# TEST GROUP: EXTENSION NORMALIZATION (normalize_extension)
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize("input_ext, expected", [
    ("py", ".py"),
    (".js", ".js"),
    ("  TXT  ", ".txt"),
    ("", ""),
    ("   ", ""),
    (".PY", ".py"),
])
def test_normalize_extension_should_ensure_leading_dot_and_lowercase(input_ext, expected):
    """Verifies file extensions are standardized for filtering logic."""
    # 1. ARRANGE & 2. ACT
    result = converters.normalize_extension(input_ext)

    # 3. ASSERT
    assert result == expected