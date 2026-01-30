from __future__ import annotations

import pytest
import io
from transcriptor4ai.shared.hashing import calculate_sha256, compute_composite_hash


# ==============================================================================
# TEST GROUP: FILE INTEGRITY HASHING (SHA-256)
# ==============================================================================

def test_calculate_sha256_should_hash_content_correctly(mocker):
    """
    Verifies that calculate_sha256 returns the correct hex digest
    for a known byte sequence using a real BytesIO stream.
    """
    # 1. ARRANGE: "Transcriptor4AI" SHA-256 verified value
    test_bytes = b"Transcriptor4AI"
    expected_hash = "1e289f0f603bf72d243dc933d205a8542cad032962755bf4e9af3b9866cd6fef"

    # Patch only the 'open' call inside the hashing module
    mock_open = mocker.patch("transcriptor4ai.shared.hashing.open")

    # Inject a real BytesIO object to satisfy the chunked reading logic
    mock_open.return_value.__enter__.return_value = io.BytesIO(test_bytes)

    # 2. ACT
    result = calculate_sha256("/fake/path/file.bin")

    # 3. ASSERT
    assert result == expected_hash


def test_calculate_sha256_should_handle_large_files_with_chunking(mocker):
    """
    Ensures the chunking logic (iterating until b"") works correctly
    for streams requiring multiple 4096-byte reads.
    """
    # 1. ARRANGE
    large_content = b"A" * 5000
    mock_open = mocker.patch("transcriptor4ai.shared.hashing.open")
    mock_open.return_value.__enter__.return_value = io.BytesIO(large_content)

    # 2. ACT
    result = calculate_sha256("/fake/path/large.bin")

    # 3. ASSERT
    assert result != ""
    assert len(result) == 64


@pytest.mark.parametrize("exception_type", [FileNotFoundError, PermissionError, OSError])
def test_calculate_sha256_should_return_empty_string_on_io_error(mocker, exception_type):
    """
    Ensures that any OS-level failure while hashing does not crash the app,
    returning an empty string as a safe fallback.
    """
    # 1. ARRANGE
    mocker.patch("builtins.open", side_effect=exception_type("System Error"))

    # 2. ACT
    result = calculate_sha256("/invalid/path")

    # 3. ASSERT
    assert result == ""


# ==============================================================================
# TEST GROUP: CACHE COMPOSITE HASHING
# ==============================================================================

def test_compute_composite_hash_should_be_deterministic():
    """
    Verifies that the same inputs always result in the same key.
    Crucial for cache hit consistency.
    """
    # 1. ARRANGE
    params = {
        "file_path": "/projects/app/main.py",
        "mtime": 1706634000.0,
        "file_size": 2048,
        "config_hash": "cfg_v2_min_true"
    }

    # 2. ACT
    hash_1 = compute_composite_hash(**params)
    hash_2 = compute_composite_hash(**params)

    # 3. ASSERT
    assert hash_1 == hash_2
    assert hash_1 != ""


@pytest.mark.parametrize("change_key, new_value", [
    ("file_path", "/projects/app/other.py"),
    ("mtime", 1706634000.1),
    ("file_size", 2049),
    ("config_hash", "cfg_v2_min_false"),
])
def test_compute_composite_hash_should_be_sensitive_to_any_change(change_key, new_value):
    """
    Ensures a cache invalidation occurs if even one metadata byte changes.
    (Avalanche effect test).
    """
    # 1. ARRANGE: Standard base state
    base_params = {
        "file_path": "/src/core.py",
        "mtime": 123456789.0,
        "file_size": 100,
        "config_hash": "default"
    }

    # 2. ACT
    original_hash = compute_composite_hash(**base_params)

    modified_params = base_params.copy()
    modified_params[change_key] = new_value
    modified_hash = compute_composite_hash(**modified_params)

    # 3. ASSERT
    assert original_hash != modified_hash, f"Hash failed to change when modifying {change_key}"