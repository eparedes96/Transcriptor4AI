from __future__ import annotations

import threading
from typing import Any

import pytest

from transcriptor4ai.application.pipeline.stages.transcriber_context import (
    generate_config_hash,
    initialize_env,
)

# ==============================================================================
# TEST GROUP: ENVIRONMENT INITIALIZATION (LOCKS & DIRS)
# ==============================================================================

@pytest.mark.unit
def test_initialize_env_creates_directories_and_locks(mocker: Any, mock_fs: Any):
    # 1. ARRANGE: Set up mocks and explicit paths requiring parent directory creation
    mock_init = mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_context.initialize_output_file")

    mod_path = "out/src/modules.txt"
    test_path = "out/test/tests.txt"
    res_path = "out/docs/resources.txt"
    err_path = "out/logs/errors.txt"

    # 2. ACT: Execute environment bootstrapping
    locks, paths = initialize_env(
        fs=mock_fs,
        modules_path=mod_path,
        tests_path=test_path,
        resources_path=res_path,
        error_path=err_path,
        processing_depth="full",
        process_tests=True,
        process_resources=True
    )

    # 3. ASSERT: Verify locks structure
    assert isinstance(locks, dict)
    assert len(locks) == 4
    for key in ["module", "test", "resource", "error"]:
        assert key in locks
        assert isinstance(locks[key], type(threading.Lock()))

    # Verify paths mapping structure
    assert paths["module"] == mod_path
    assert paths["test"] == test_path
    assert paths["resource"] == res_path
    assert paths["error"] == err_path

    # Verify parent directory creation calls
    # Extracts the directory part (e.g., 'out/src') and calls safe_mkdir
    mock_fs.safe_mkdir.assert_any_call("out/src")
    mock_fs.safe_mkdir.assert_any_call("out/test")
    mock_fs.safe_mkdir.assert_any_call("out/docs")
    mock_fs.safe_mkdir.assert_any_call("out/logs")
    assert mock_fs.safe_mkdir.call_count == 4


@pytest.mark.unit
def test_initialize_env_handles_paths_without_parent_directories(mocker: Any, mock_fs: Any):
    # 1. ARRANGE: Provide flat filenames without slashes
    mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_context.initialize_output_file")

    # 2. ACT
    initialize_env(
        fs=mock_fs,
        modules_path="modules.txt",
        tests_path="tests.txt",
        resources_path="resources.txt",
        error_path="errors.txt",
        processing_depth="full",
        process_tests=True,
        process_resources=True
    )

    # 3. ASSERT: safe_mkdir should NOT be called if there is no parent directory extracted
    mock_fs.safe_mkdir.assert_not_called()


# ==============================================================================
# TEST GROUP: HEADER INJECTION LOGIC
# ==============================================================================

@pytest.mark.unit
@pytest.mark.parametrize(
    "depth, process_tests, process_resources, expected_init_calls", [
        # Full features enabled
        ("full", True, True, ["modules_path", "tests_path", "resources_path"]),
        # Skeleton depth is treated like 'full' for initialization purposes
        ("skeleton", True, False, ["modules_path", "tests_path"]),
        # Tree only: Excludes modules logic
        ("tree_only", True, True, ["tests_path", "resources_path"]),
        # Minimal run
        ("tree_only", False, False, []),
    ]
)
def test_initialize_env_respects_depth_and_feature_flags(
        mocker: Any,
        mock_fs: Any,
        depth: str,
        process_tests: bool,
        process_resources: bool,
        expected_init_calls: list[str]
):
    # 1. ARRANGE
    mock_init = mocker.patch("transcriptor4ai.application.pipeline.stages.transcriber_context.initialize_output_file")

    path_map = {
        "modules_path": "/tmp/mod.txt",
        "tests_path": "/tmp/tst.txt",
        "resources_path": "/tmp/res.txt",
    }

    # 2. ACT
    initialize_env(
        fs=mock_fs,
        modules_path=path_map["modules_path"],
        tests_path=path_map["tests_path"],
        resources_path=path_map["resources_path"],
        error_path="/tmp/err.txt",
        processing_depth=depth,
        process_tests=process_tests,
        process_resources=process_resources
    )

    # 3. ASSERT
    assert mock_init.call_count == len(expected_init_calls)

    # Verify specific files were initialized based on the parameterized expectation
    called_paths = [call.args[0] for call in mock_init.call_args_list]
    for key in expected_init_calls:
        assert path_map[key] in called_paths


# ==============================================================================
# TEST GROUP: CONFIGURATION HASHING
# ==============================================================================

@pytest.mark.unit
def test_generate_config_hash_is_deterministic_and_unique():
    # 1. ARRANGE
    args_baseline = ("full", True, False, True, False, True)
    args_altered = ("full", True, False, True, True, True)  # Changed 5th parameter

    # 2. ACT
    hash_1 = generate_config_hash(*args_baseline)
    hash_2 = generate_config_hash(*args_baseline)
    hash_3 = generate_config_hash(*args_altered)

    # 3. ASSERT
    # Must be deterministic (same input = same output)
    assert hash_1 == hash_2

    # Must be sensitive to changes (different input = different output)
    assert hash_1 != hash_3

    # Must follow MD5 format (32 character hex string)
    assert len(hash_1) == 32
    assert all(c in "0123456789abcdef" for c in hash_1)