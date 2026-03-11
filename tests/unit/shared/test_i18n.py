import json

import pytest

from transcriptor4ai.shared.i18n import I18n

# ==============================================================================
# TEST GROUP: LOCALIZATION LOGIC (I18n)
# ==============================================================================

@pytest.fixture
def sample_translations():
    """Provides a controlled translation dictionary."""
    return {
        "app": {"name": "TestApp"},
        "gui": {
            "buttons": {
                "save": "Save",
                "welcome": "Hello {name}!"
            }
        }
    }


@pytest.mark.unit
def test_load_locale_successfully_populates_data(mocker, sample_translations):
    """Verifies that a valid JSON file is correctly loaded into the instance."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps(sample_translations)))
    instance = I18n(locale="en")

    # 2. ACT
    # Initialization calls load_locale automatically

    # 3. ASSERT
    assert instance.is_loaded is True
    assert instance.t("app.name") == "TestApp"


@pytest.mark.unit
def test_load_locale_fails_gracefully_when_file_missing(mocker):
    """Ensures the system doesn't crash if a locale file is missing on disk."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=False)

    # 2. ACT
    instance = I18n(locale="non_existent")

    # 3. ASSERT
    assert instance.is_loaded is False
    # Should return the key itself as fallback
    assert instance.t("any.key") == "any.key"


@pytest.mark.unit
def test_load_locale_handles_corrupted_json(mocker):
    """Validates resilience against malformed JSON files."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data="{ invalid json: "))

    # 2. ACT
    instance = I18n(locale="en")

    # 3. ASSERT
    assert instance.is_loaded is False
    assert instance._translations == {}


@pytest.mark.unit
def test_translate_resolves_nested_keys(mocker, sample_translations):
    """Verifies recursive resolution of dot-notation keys (e.g., a.b.c)."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps(sample_translations)))
    instance = I18n(locale="en")

    # 2. ACT & 3. ASSERT
    assert instance.t("gui.buttons.save") == "Save"


@pytest.mark.unit
def test_translate_performs_variable_interpolation(mocker, sample_translations):
    """Ensures that variables provided in kwargs are correctly injected into strings."""
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps(sample_translations)))
    instance = I18n(locale="en")

    # 2. ACT
    result = instance.t("gui.buttons.welcome", name="Senior SDET")

    # 3. ASSERT
    assert result == "Hello Senior SDET!"


@pytest.mark.unit
@pytest.mark.parametrize("invalid_key", [
    "gui.buttons",  # Points to a Dict, not a String
    "app.missing",  # Key doesn't exist
    "totally.wrong",  # Root doesn't exist
    "",  # Empty key
])
def test_translate_returns_key_on_resolution_failure(mocker, sample_translations, invalid_key):
    """
    Critical for UX: If a key is invalid or incomplete, return the key
    itself to allow developers to spot missing translations easily.
    """
    # 1. ARRANGE
    mocker.patch("os.path.exists", return_value=True)
    mocker.patch("builtins.open", mocker.mock_open(read_data=json.dumps(sample_translations)))
    instance = I18n(locale="en")

    # 2. ACT
    result = instance.t(invalid_key)

    # 3. ASSERT
    assert result == invalid_key


@pytest.mark.unit
def test_path_resolution_logic_supports_frozen_environment(mocker):
    """
    Verifies that the class correctly identifies the _MEIPASS directory
    when running as a PyInstaller executable.
    """
    # 1. ARRANGE: Simulate frozen environment
    mocker.patch("sys.frozen", True, create=True)
    mocker.patch("sys._MEIPASS", "/tmp/internal_pkg", create=True)
    mocker.patch("os.path.exists", return_value=False)  # To avoid loading real files

    # 2. ACT
    instance = I18n(locale="en")

    # 3. ASSERT
    # Expecting path to point to the internal PyInstaller dir
    assert "internal_pkg" in instance._locales_path
    assert "interface" in instance._locales_path