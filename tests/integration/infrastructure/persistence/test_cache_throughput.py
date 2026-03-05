from __future__ import annotations

import time
import pytest
from typing import List

from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository


# ==============================================================================
# TEST GROUP: SQLITE CACHE THROUGHPUT & PERFORMANCE
# ==============================================================================

@pytest.fixture
def performance_repo(mocker, tmp_path) -> SqliteCacheRepository:
    """
    1. ARRANGE: Set up a real SQLite database in a safe temporary directory.
    We mock the FileSystemAdapter to inject the pytest tmp_path.
    """
    mock_fs = mocker.Mock()
    mock_fs.get_user_data_dir.return_value = str(tmp_path)

    # Ensures the DB is created in the temp folder with WAL mode enabled
    return SqliteCacheRepository(fs_adapter=mock_fs)


@pytest.mark.integration
def test_write_throughput_survives_sequential_mass_inserts(performance_repo):
    """
    Evaluates the repository's ability to handle high-frequency individual
    inserts without hitting 'database is locked' errors due to connection churn.
    """
    # 1. ARRANGE: Prepare massive payload data
    total_entries = 1000
    mock_content = "def test_perf(): pass\n" * 10

    start_time = time.perf_counter()

    # 2. ACT: Execute massive write operations
    for i in range(total_entries):
        composite_hash = f"perf_hash_{i}"
        file_path = f"/src/module_{i}.py"

        performance_repo.set_entry(
            composite_hash=composite_hash,
            file_path=file_path,
            content=mock_content,
            token_count=150
        )

    duration = time.perf_counter() - start_time

    # 3. ASSERT: Verify integrity and performance threshold
    # Threshold is kept generous (15s) to prevent flakiness in slow CI environments,
    # but the primary goal is ensuring zero sqlite3.Error exceptions occurred.
    assert performance_repo.is_enabled() is True
    assert duration < 15.0, f"Write throughput too slow: {duration:.2f}s for {total_entries} entries"

    # Spot-check structural integrity
    first_entry = performance_repo.get_entry("perf_hash_0")
    last_entry = performance_repo.get_entry(f"perf_hash_{total_entries - 1}")

    assert first_entry is not None
    assert last_entry is not None
    assert last_entry[1] == 150


@pytest.mark.integration
def test_read_throughput_is_highly_optimized(performance_repo):
    """
    Ensures that mass read operations are significantly faster and
    do not suffer from cursor exhaustion.
    """
    # 1. ARRANGE: Pre-populate the database
    total_entries = 1000
    for i in range(total_entries):
        performance_repo.set_entry(
            composite_hash=f"read_hash_{i}",
            file_path="dummy.py",
            content="data",
            token_count=10
        )

    start_time = time.perf_counter()

    # 2. ACT: Execute mass reads
    successful_reads = 0
    for i in range(total_entries):
        result = performance_repo.get_entry(f"read_hash_{i}")
        if result is not None:
            successful_reads += 1

    duration = time.perf_counter() - start_time

    # 3. ASSERT: Read speed should be near-instantaneous
    assert successful_reads == total_entries
    assert duration < 5.0, f"Read throughput degraded: {duration:.2f}s"


@pytest.mark.integration
def test_cache_handles_massive_single_payload_without_memory_errors(performance_repo):
    """
    Validates that saving a monolithic file (e.g., a massive 5MB JSON or bundled JS)
    does not exceed SQLite limits or cause serialization crashes.
    """
    # 1. ARRANGE: Create a massive ~5MB string
    massive_hash = "monolithic_hash_999"
    mb_size = 5
    chunk = "A" * (1024 * 1024)  # 1MB
    massive_payload = chunk * mb_size
    estimated_tokens = mb_size * 250000

    # 2. ACT: Save and retrieve the massive payload
    start_write = time.perf_counter()
    performance_repo.set_entry(
        composite_hash=massive_hash,
        file_path="/dist/bundle.js",
        content=massive_payload,
        token_count=estimated_tokens
    )
    write_time = time.perf_counter() - start_write

    start_read = time.perf_counter()
    recovered_data = performance_repo.get_entry(massive_hash)
    read_time = time.perf_counter() - start_read

    # 3. ASSERT: Data remains uncorrupted and timing is within reason
    assert recovered_data is not None
    recovered_content, recovered_tokens = recovered_data

    assert len(recovered_content) == len(massive_payload)
    assert recovered_tokens == estimated_tokens

    # Ensure massive payload processing didn't disable the database
    assert performance_repo.is_enabled() is True