from __future__ import annotations

# ==============================================================================
# TEST GROUP: APP CONFIGURATION ENTITY
# ==============================================================================
import pytest

from transcriptor4ai.domain.entities.app_config import (
    apply_config_integrity,
    get_default_app_state,
    get_default_config,
)
from transcriptor4ai.domain.entities.formatting_options import OutputFormat

# 1. ARRANGE: Shared constants for the test group
FAKE_PATH = "/path/to/project"


def test_get_default_config_completeness():
    """
    Ensures that the default configuration contains all critical keys
    required for the v2.2 pipeline execution, including new formatting options.
    """
    # 2. ACT: Generate default configuration
    cfg = get_default_config(FAKE_PATH)

    # 3. ASSERT: Verify presence of mandatory schema keys
    required_keys = [
        "input_path", "output_base_dir", "output_subdir_name",
        "process_modules", "processing_depth", "process_tests",
        "create_individual_files", "create_unified_file",
        "target_model", "generate_tree", "enable_sanitizer",
        "output_format", "custom_preamble"
    ]

    for key in required_keys:
        assert key in cfg, f"Missing mandatory key in default config: {key}"

    assert cfg["output_format"] == "plaintext"
    assert cfg["custom_preamble"] == ""


def test_get_default_app_state_structure():
    """
    Verifies the root application state structure (config.json schema).
    """
    # 2. ACT
    state = get_default_app_state(FAKE_PATH)

    # 3. ASSERT
    assert "version" in state
    assert "app_settings" in state
    assert "last_session" in state
    assert "saved_profiles" in state
    assert isinstance(state["app_settings"], dict)
    assert state["last_session"]["input_path"] == FAKE_PATH


@pytest.mark.parametrize("initial_depth, process_modules, expected_depth", [
    ("full", False, "tree_only"),
    ("skeleton", False, "tree_only"),
    ("tree_only", False, "tree_only"),
])
def test_integrity_disabling_modules_forces_tree_only(initial_depth, process_modules, expected_depth):
    """
    Business Rule: If source logic (modules) is disabled,
    the processing depth MUST be 'tree_only'.
    """
    # 1. ARRANGE
    cfg = {
        "process_modules": process_modules,
        "processing_depth": initial_depth
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    # Ensures the depth is corrected to avoid processing files without logic
    assert cfg["processing_depth"] == expected_depth


def test_integrity_tree_only_depth_forces_no_modules():
    """
    Business Rule: If depth is explicitly set to 'tree_only',
    the 'process_modules' flag MUST be False.
    """
    # 1. ARRANGE
    cfg = {
        "process_modules": True,
        "processing_depth": "tree_only"
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    # Synchronizes modules flag with the structural-only mode
    assert cfg["process_modules"] is False


@pytest.mark.parametrize("raw_input, expected_output", [
    ("  XML  ", "xml"),  # Normalizes casing and whitespace
    ("MARKDOWN", "markdown"),  # Validates existing formats
    ("invalid_format", "plaintext")  # Falls back to plaintext on garbage input
])
def test_integrity_normalizes_output_format(raw_input, expected_output):
    """
    Ensures that the output_format is always a valid string recognized
    by the domain Enum.
    """
    # 1. ARRANGE
    cfg = {"output_format": raw_input}

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    assert cfg["output_format"] == expected_output


def test_integrity_cleans_custom_preamble():
    """
    Verifies that preambles are trimmed and non-string values are
    handled gracefully to avoid crashes during assembly.
    """
    # 1. ARRANGE
    cfg = {
        "custom_preamble": "   Act as an SDET.   ",
        "bad_preamble": 12345
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT
    # Normalizes valid string
    assert cfg["custom_preamble"] == "Act as an SDET."

    # Manages type mismatch for the preamble key
    # (Testing the logic indirectly as the function uses .get())
    broken_cfg = {"custom_preamble": 123}
    apply_config_integrity(broken_cfg)
    assert broken_cfg["custom_preamble"] == ""


def test_integrity_forces_unified_file_for_xml_format():
    """
    Critical Rule: XML output requires a root node, so it cannot be
    distributed across individual files without losing context.
    """
    # 1. ARRANGE: User wants XML but tries to disable unified file
    cfg = {
        "output_format": "xml",
        "create_unified_file": False
    }

    # 2. ACT
    apply_config_integrity(cfg)

    # 3. ASSERT: System overrides user choice for technical validity
    # Ensures the context remains valid for the LLM
    assert cfg["create_unified_file"] is True


def test_integrity_preserves_valid_config():
    """
    Ensures that a logically consistent configuration is not
    mutated by the integrity checker.
    """
    # 1. ARRANGE
    valid_cfg = {
        "process_modules": True,
        "processing_depth": "skeleton",
        "output_format": "markdown",
        "create_unified_file": True,
        "custom_preamble": "Test preamble"
    }
    original_cfg = valid_cfg.copy()

    # 2. ACT
    apply_config_integrity(valid_cfg)

    # 3. ASSERT
    # No changes should occur for a valid state
    assert valid_cfg == original_cfg