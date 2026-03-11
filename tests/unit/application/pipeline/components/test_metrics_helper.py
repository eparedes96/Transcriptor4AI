from __future__ import annotations

from typing import Any, Dict

import pytest

from transcriptor4ai.application.pipeline.components.metrics_helper import (
    increment_mode_counters,
    initialize_results_dict,
)

# ==============================================================================
# TEST GROUP: METRICS INITIALIZATION
# ==============================================================================

@pytest.mark.unit
def test_initialize_results_dict_creates_complete_schema():
    # 1. ARRANGE & ACT
    results = initialize_results_dict()

    # 3. ASSERT
    expected_keys = [
        "processed",
        "cached",
        "skipped",
        "total_tokens",
        "tests_written",
        "modules_written",
        "resources_written",
        "errors",
    ]
    for key in expected_keys:
        assert key in results, f"Missing required key: {key}"

    # Verify initial types and values
    assert results["processed"] == 0
    assert results["total_tokens"] == 0
    assert isinstance(results["errors"], list)
    assert len(results["errors"]) == 0


# ==============================================================================
# TEST GROUP: COUNTER INCREMENTS & ROUTING
# ==============================================================================

@pytest.fixture
def base_results() -> Dict[str, Any]:
    """Provides a fresh, zeroed-out results dictionary for mutation tests."""
    return initialize_results_dict()


@pytest.mark.unit
@pytest.mark.parametrize(
    "file_name, process_tests, process_resources, expected_counter", [
        # Standard Code Modules
        ("main.py", True, True, "modules_written"),
        ("controller.js", False, False, "modules_written"),

        # Tests detection and routing
        ("test_main.py", True, True, "tests_written"),
        ("AppTest.java", True, False, "tests_written"),
        ("test_utils.py", False, True, "modules_written"),  # Fallback behavior if disabled

        # Resources detection and routing
        ("README.md", True, True, "resources_written"),
        ("config.json", False, True, "resources_written"),
        ("Dockerfile", False, False, "modules_written"),  # Fallback behavior if disabled
    ]
)
def test_increment_mode_counters_routes_to_correct_metric(
        base_results: Dict[str, Any],
        file_name: str,
        process_tests: bool,
        process_resources: bool,
        expected_counter: str
):
    # 1. ARRANGE: Set up the specific file metadata
    file_data = {"file_name": file_name}
    processing_depth = "full"

    # Verify pre-condition
    assert base_results[expected_counter] == 0

    # 2. ACT: Execute the counter logic (mutates base_results in-place)
    increment_mode_counters(
        file_data=file_data,
        results=base_results,
        processing_depth=processing_depth,
        process_tests=process_tests,
        process_resources=process_resources
    )

    # 3. ASSERT: Verify only the expected counter was incremented
    assert base_results[expected_counter] == 1

    # Check that other counters were NOT incremented
    other_counters = {"modules_written", "tests_written", "resources_written"} - {expected_counter}
    for other in other_counters:
        assert base_results[other] == 0


# ==============================================================================
# TEST GROUP: EDGE CASES & CONFIG CONSTRAINTS
# ==============================================================================

@pytest.mark.unit
def test_increment_mode_counters_skips_when_depth_is_tree_only(base_results: Dict[str, Any]):
    # 1. ARRANGE
    file_data = {"file_name": "main.py"}

    # 2. ACT
    # If processing_depth is 'tree_only', no writing counters should increase
    increment_mode_counters(
        file_data=file_data,
        results=base_results,
        processing_depth="tree_only",
        process_tests=True,
        process_resources=True
    )

    # 3. ASSERT
    assert base_results["modules_written"] == 0
    assert base_results["tests_written"] == 0
    assert base_results["resources_written"] == 0


@pytest.mark.unit
def test_increment_mode_counters_handles_missing_file_name_gracefully(base_results: Dict[str, Any]):
    # 1. ARRANGE
    # A dictionary completely missing the "file_name" key
    file_data: Dict[str, Any] = {}

    # 2. ACT
    increment_mode_counters(
        file_data=file_data,
        results=base_results,
        processing_depth="full",
        process_tests=True,
        process_resources=True
    )

    # 3. ASSERT
    # Empty string defaults to module logic (not a test, not a resource)
    assert base_results["modules_written"] == 1


@pytest.mark.unit
def test_increment_mode_counters_creates_keys_if_missing_in_results():
    # 1. ARRANGE
    # Simulating a scenario where the dictionary was not initialized correctly
    empty_results: Dict[str, Any] = {}
    file_data = {"file_name": "app.py"}

    # 2. ACT
    # Uses .get(key, 0) under the hood, so it should not raise a KeyError
    increment_mode_counters(
        file_data=file_data,
        results=empty_results,
        processing_depth="skeleton",
        process_tests=True,
        process_resources=True
    )

    # 3. ASSERT
    assert "modules_written" in empty_results
    assert empty_results["modules_written"] == 1