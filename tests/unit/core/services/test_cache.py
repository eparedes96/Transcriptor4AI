from __future__ import annotations

"""
Unit tests for the Local Cache Service.

Verifies:
1. SQLite database initialization and schema creation.
2. Read/Write operations (Set/Get) including token counts.
3. Deterministic hashing logic.
4. Purging mechanism.
5. Fail-safe behavior (exceptions should not crash the app).
"""

from typing import Any, Generator
from unittest.mock import patch

import pytest

from transcriptor4ai.core.services.cache import CacheService


@pytest.fixture
def mock_cache_service(tmp_path: Any) -> Generator[CacheService, None, None]:
    """
    Provide a CacheService instance using a temporary directory.

    Prevents tests from modifying the real user data directory.

    Args:
        tmp_path: Pytest fixture for temporary directory creation.

    Yields:
        CacheService: Initialized service pointing to a temporary DB.
    """
    with patch("transcriptor4ai.core.services.cache.get_user_data_dir", return_value=str(tmp_path)):
        service = CacheService()
        yield service


def test_cache_initialization_creates_db(mock_cache_service: CacheService, tmp_path: Any) -> None:
    """
    Verify that the database file is created upon service initialization.
    """
    db_path = tmp_path / "cache.db"
    assert db_path.exists()
    assert mock_cache_service._enabled is True


def test_set_and_get_entry(mock_cache_service: CacheService) -> None:
    """
    Verify a complete write and read lifecycle for a cache entry including tokens.
    """
    dummy_hash = "abc123hash"
    dummy_path = "/src/main.py"
    content = "def main(): pass"
    token_count = 150

    mock_cache_service.set_entry(dummy_hash, dummy_path, content, token_count)

    retrieved = mock_cache_service.get_entry(dummy_hash)

    # Verify both content and persisted token count
    assert retrieved is not None
    assert retrieved == (content, token_count)


def test_get_non_existent_entry_returns_none(mock_cache_service: CacheService) -> None:
    """
    Ensure that a cache miss returns None instead of raising an exception.
    """
    assert mock_cache_service.get_entry("fake_hash") is None


def test_hashing_is_deterministic(mock_cache_service: CacheService) -> None:
    """
    Verify that the composite hashing logic is deterministic and sensitive to inputs.
    """
    params = {
        "file_path": "/abs/path/file.py",
        "mtime": 1700000000.0,
        "file_size": 1024,
        "config_hash": "cfg_v1"
    }

    hash1 = mock_cache_service.compute_composite_hash(**params)
    hash2 = mock_cache_service.compute_composite_hash(**params)

    # Determinism
    assert hash1 == hash2
    assert len(hash1) == 64

    # Sensitivity
    params["file_size"] = 1025
    hash3 = mock_cache_service.compute_composite_hash(**params)
    assert hash1 != hash3


def test_purge_all_clears_data(mock_cache_service: CacheService) -> None:
    """
    Verify that the purge mechanism removes all entries from the database.
    """
    mock_cache_service.set_entry("h1", "p1", "c1", 50)
    assert mock_cache_service.get_entry("h1") == ("c1", 50)

    mock_cache_service.purge_all()
    assert mock_cache_service.get_entry("h1") is None


def test_resilience_to_corruption(mock_cache_service: CacheService, tmp_path: Any) -> None:
    """
    Verify that the service handles a corrupted database file gracefully.
    """
    db_path = tmp_path / "cache.db"

    # Corrupt the database file with invalid data
    with open(db_path, "wb") as f:
        f.write(b"NOT_A_SQLITE_DB_CONTENT")

    # Re-initialize service against the corrupted file
    with patch("transcriptor4ai.core.services.cache.get_user_data_dir", return_value=str(tmp_path)):
        service = CacheService()

        # The service should either disable itself or handle the error on access
        if service._enabled:
            val = service.get_entry("any_hash")
            assert val is None
        else:
            assert service._enabled is False