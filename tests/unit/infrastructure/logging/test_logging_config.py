import logging
from dataclasses import FrozenInstanceError

import pytest

from transcriptor4ai.infrastructure.logging.logging_config import LoggingConfig, _LEVEL_MAP

# ==============================================================================
# TEST GROUP: LOGGING CONFIGURATION CONTRACT
# ==============================================================================

def test_logging_config_should_initialize_with_sane_defaults():
    """
    Verifies that a fresh instance of LoggingConfig contains the
    industrial-standard defaults defined in the specification.
    """
    # 1. ARRANGE & 2. ACT
    config = LoggingConfig()

    # 3. ASSERT
    assert config.level == "INFO"
    assert config.console is True
    assert config.log_file is None
    assert config.max_bytes == 2 * 1024 * 1024  # 2MB
    assert config.backup_count == 3
    assert "%(levelname)s" in config.console_fmt
    assert "%(asctime)s" in config.file_fmt


def test_logging_config_should_allow_custom_values():
    """
    Verifies that custom parameters are correctly assigned during instantiation.
    """
    # 1. ARRANGE
    custom_path = "/tmp/transcriptor.log"
    custom_level = "DEBUG"

    # 2. ACT
    config = LoggingConfig(
        level=custom_level,
        log_file=custom_path,
        console=False,
        backup_count=10
    )

    # 3. ASSERT
    assert config.level == "DEBUG"
    assert config.log_file == custom_path
    assert config.console is False
    assert config.backup_count == 10


def test_logging_config_is_immutable_by_design():
    """
    Ensures the dataclass is frozen. Any attempt to modify it at runtime
    should raise a FrozenInstanceError.
    """
    # 1. ARRANGE
    config = LoggingConfig()

    # 2. ACT & 3. ASSERT
    # Critical: Configuration must be read-only to prevent race conditions
    # during background logging initialization.
    # We catch FrozenInstanceError which is raised by frozen dataclasses.
    with pytest.raises(FrozenInstanceError):
        config.level = "CRITICAL"


@pytest.mark.parametrize("level_name, expected_const", [
    ("DEBUG", logging.DEBUG),
    ("INFO", logging.INFO),
    ("WARNING", logging.WARNING),
    ("WARN", logging.WARNING),
    ("ERROR", logging.ERROR),
    ("CRITICAL", logging.CRITICAL),
])
def test_level_map_should_contain_all_standard_python_levels(level_name, expected_const):
    """
    Validates that the string-to-int mapping correctly translates
    human-readable levels to Python logging constants.
    """
    # 1. ACT
    mapped_value = _LEVEL_MAP.get(level_name)

    # 2. ASSERT
    assert mapped_value == expected_const


def test_level_map_integrity_should_match_all_expected_keys():
    """
    Ensures no critical logging levels were omitted from the internal map.
    """
    # 1. ARRANGE
    expected_keys = {"DEBUG", "INFO", "WARNING", "WARN", "ERROR", "CRITICAL"}

    # 2. ACT
    current_keys = set(_LEVEL_MAP.keys())

    # 3. ASSERT
    assert expected_keys.issubset(current_keys)