import threading
import pytest
from concurrent.futures import ThreadPoolExecutor
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository


# ==============================================================================
# TEST GROUP: SQLITE CACHE CONCURRENCY & STRESS
# ==============================================================================

@pytest.fixture
def thread_safe_repo(mocker, tmp_path):
    """
    Provides a real SqliteCacheRepository pointing to a temp directory.
    We use a real disk file instead of :memory: to test true OS file locking.
    """
    mock_fs = mocker.Mock()
    mock_fs.get_user_data_dir.return_value = str(tmp_path)
    repo = SqliteCacheRepository(fs_adapter=mock_fs)
    return repo


@pytest.mark.integration
def test_cache_handles_massive_concurrent_writes(thread_safe_repo):
    """
    Verifies that multiple threads can write unique entries simultaneously
    without triggering 'database is locked' errors.
    """
    # 1. ARRANGE
    num_threads = 50
    entries_per_thread = 10

    def worker(worker_id: int):
        for i in range(entries_per_thread):
            composite_hash = f"hash_{worker_id}_{i}"
            thread_safe_repo.set_entry(
                composite_hash=composite_hash,
                file_path=f"/path/to/file_{worker_id}_{i}.py",
                content=f"Content from worker {worker_id}",
                token_count=100
            )

    # 2. ACT
    # Using ThreadPoolExecutor to simulate heavy thread contention
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker, i) for i in range(num_threads)]
        for future in futures:
            future.result()  # Should not raise sqlite3.OperationalError

    # 3. ASSERT
    # Verify that all records were actually persisted
    expected_total = num_threads * entries_per_thread

    # We query directly through the repo to check internal state
    hits = 0
    for w in range(num_threads):
        for i in range(entries_per_thread):
            if thread_safe_repo.get_entry(f"hash_{w}_{i}"):
                hits += 1

    assert hits == expected_total


@pytest.mark.integration
def test_cache_consistency_under_read_write_race(thread_safe_repo):
    """
    Ensures that reading from the cache while other threads are writing
    does not cause data corruption or crashes.
    """
    # 1. ARRANGE
    stop_event = threading.Event()
    target_hash = "shared_target"

    def writer():
        counter = 0
        while not stop_event.is_set():
            thread_safe_repo.set_entry(target_hash, "file.py", f"val_{counter}", counter)
            counter += 1

    def reader():
        while not stop_event.is_set():
            # Entry might be None initially or a tuple
            res = thread_safe_repo.get_entry(target_hash)
            if res:
                content, tokens = res
                assert content.startswith("val_")
                assert isinstance(tokens, int)

    # 2. ACT
    threads = [
        threading.Thread(target=writer),
        threading.Thread(target=reader),
        threading.Thread(target=reader)
    ]

    for t in threads: t.start()
    import time
    time.sleep(1.0)  # Let them race for 1 second
    stop_event.set()
    for t in threads: t.join()

    # 3. ASSERT
    # Final state should be valid
    final_entry = thread_safe_repo.get_entry(target_hash)
    assert final_entry is not None


@pytest.mark.integration
def test_cache_purge_during_active_operations(thread_safe_repo):
    """
    Critical Scenario: A user triggers 'Purge Cache' via GUI while the
    pipeline workers are still writing data.
    """
    # 1. ARRANGE
    num_writes = 100
    exceptions = []

    def heavy_writer():
        try:
            for i in range(num_writes):
                thread_safe_repo.set_entry(f"h_{i}", "p.py", "c", i)
        except Exception as e:
            exceptions.append(e)

    # 2. ACT
    write_thread = threading.Thread(target=heavy_writer)
    write_thread.start()

    # Attempt to purge mid-way
    thread_safe_repo.purge_all()

    write_thread.join()

    # 3. ASSERT
    # Purge + Write should not crash the system
    # Note: Depending on timing, some writes might persist after purge or fail gracefully
    assert len(exceptions) == 0, f"Purge caused thread failures: {exceptions}"
    assert thread_safe_repo.is_enabled() is True


@pytest.mark.integration
def test_cache_upsert_contention_same_key(thread_safe_repo):
    """
    Scenario: Multiple workers finish processing the same file (e.g. symlinks)
    and try to update the same cache key simultaneously.
    """
    # 1. ARRANGE
    shared_hash = "collision_hash"
    num_contenders = 20

    def contender(cid):
        thread_safe_repo.set_entry(shared_hash, "path.py", f"content_{cid}", cid)

    # 2. ACT
    with ThreadPoolExecutor(max_workers=num_contenders) as executor:
        executor.map(contender, range(num_contenders))

    # 3. ASSERT
    # Database should be intact and contain one of the values
    result = thread_safe_repo.get_entry(shared_hash)
    assert result is not None
    content, tokens = result
    assert content.startswith("content_")
    # Exact value depends on which thread won the last race, but it must be valid