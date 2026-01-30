# ==============================================================================
# TEST GROUP: SQLITE CACHE REPOSITORY (INTEGRATION)
# ==============================================================================

import os
import sqlite3
import pytest
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository


@pytest.fixture
def mock_fs(mocker, tmp_path):
    """
    Mocks the IFileSystem port to redirect the database file
    to a secure temporary directory.
    """
    fs = mocker.Mock()
    # Ensure the DB is created in the pytest temp folder
    fs.get_user_data_dir.return_value = str(tmp_path)
    return fs


@pytest.fixture
def cache_repo(mock_fs):
    """
    Provides a fresh SqliteCacheRepository instance for each test.
    """
    return SqliteCacheRepository(fs_adapter=mock_fs)


@pytest.mark.integration
def test_sqlite_cache_initialization_creates_schema(cache_repo, tmp_path):
    """
    Ensures that the database file is created and the schema (including
    v2.1 token_count column) is correctly initialized.
    """
    # 1. ARRANGE: Define path
    db_path = tmp_path / SqliteCacheRepository.DB_FILENAME

    # 2. ACT: Initialization happens in fixture

    # 3. ASSERT: Verify file exists and columns are present
    assert db_path.exists()

    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(file_cache)")
    columns = [row[1] for row in cursor.fetchall()]
    conn.close()

    assert "composite_hash" in columns
    assert "content" in columns
    assert "token_count" in columns  # Verification of v2.1 migration


@pytest.mark.integration
def test_sqlite_cache_set_and_get_lifecycle(cache_repo):
    """
    Validates the full write-read cycle for a processed file.
    """
    # 1. ARRANGE
    c_hash = "sha256_mock_hash_val"
    f_path = "/src/app.py"
    content = "def hello(): pass"
    tokens = 42

    # 2. ACT
    cache_repo.set_entry(c_hash, f_path, content, tokens)
    result = cache_repo.get_entry(c_hash)

    # 3. ASSERT
    assert result is not None
    cached_content, cached_tokens = result
    assert cached_content == content
    assert cached_tokens == tokens


@pytest.mark.integration
def test_sqlite_cache_upsert_replaces_existing_entry(cache_repo):
    """
    Ensures that inserting an entry with an existing hash updates
    the content instead of creating a duplicate or failing.
    """
    # 1. ARRANGE
    c_hash = "constant_hash"
    cache_repo.set_entry(c_hash, "old.py", "old content", 10)

    # 2. ACT: Update with same hash
    new_content = "updated content"
    cache_repo.set_entry(c_hash, "new.py", new_content, 20)

    # 3. ASSERT
    result = cache_repo.get_entry(c_hash)
    assert result[0] == new_content
    assert result[1] == 20


@pytest.mark.integration
def test_sqlite_cache_persistence_across_instances(mock_fs):
    """
    Validates that data is physically persisted to disk and can
    be retrieved by a new repository instance.
    """
    # 1. ARRANGE
    c_hash = "persistence_test_hash"
    repo1 = SqliteCacheRepository(fs_adapter=mock_fs)
    repo1.set_entry(c_hash, "test.py", "persisted data", 100)

    # 2. ACT: Instantiate a new repo instance pointing to same file
    repo2 = SqliteCacheRepository(fs_adapter=mock_fs)
    result = repo2.get_entry(c_hash)

    # 3. ASSERT
    assert result is not None
    assert result[0] == "persisted data"


@pytest.mark.integration
def test_sqlite_cache_get_non_existent_returns_none(cache_repo):
    """
    Verify that cache misses return None gracefully.
    """
    # 2. ACT
    result = cache_repo.get_entry("non_existent_hash")

    # 3. ASSERT
    assert result is None


@pytest.mark.integration
def test_sqlite_cache_purge_all_clears_database(cache_repo):
    """
    Ensures that purge_all removes all entries and maintains DB integrity.
    """
    # 1. ARRANGE
    cache_repo.set_entry("h1", "p1", "c1", 1)
    cache_repo.set_entry("h2", "p2", "c2", 2)

    # 2. ACT
    cache_repo.purge_all()

    # 3. ASSERT
    assert cache_repo.get_entry("h1") is None
    assert cache_repo.get_entry("h2") is None


@pytest.mark.integration
def test_sqlite_cache_resilience_to_corruption(mock_fs, tmp_path):
    """
    Ensures the application does not crash if the database file
    is corrupted. The repo should disable itself gracefully.
    """
    # 1. ARRANGE: Create a corrupted file where the DB should be
    db_path = tmp_path / SqliteCacheRepository.DB_FILENAME
    with open(db_path, "w") as f:
        f.write("THIS IS NOT A SQLITE DATABASE")

    # 2. ACT
    corrupt_repo = SqliteCacheRepository(fs_adapter=mock_fs)

    # 3. ASSERT
    # Repo should have detected the failure and disabled itself
    assert corrupt_repo.is_enabled() is False
    # Operations should return None but not raise exceptions
    assert corrupt_repo.get_entry("any_hash") is None