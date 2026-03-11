# ==============================================================================
# TEST GROUP: PROJECT SCANNER SCALING & PERFORMANCE
# ==============================================================================

import re
import time

import pytest

from transcriptor4ai.application.services.project_scanner import ProjectScannerService

# Ensures the scanner can handle large-scale projects (10k+ files) efficiently
# without excessive memory consumption or performance degradation.

@pytest.fixture
def scanner(mock_fs):
    """Returns a scanner instance with a mocked filesystem port."""
    return ProjectScannerService(mock_fs)


def test_scanner_should_handle_ten_thousand_files_efficiently(mocker, scanner):
    # 1. ARRANGE: Simulate a massive project structure via os.walk mock
    total_files = 10000
    # Generate a list of (root, dirs, files) tuples
    # 100 directories, each with 100 files
    massive_structure = []
    for i in range(100):
        dir_path = f"/root/dir_{i}"
        filenames = [f"file_{j}.py" for j in range(100)]
        massive_structure.append((dir_path, [], filenames))

    mocker.patch("os.walk", return_value=massive_structure)
    mocker.patch("os.path.abspath", side_effect=lambda x: x)

    # Generic filters
    include_rx = [re.compile(r".*")]
    exclude_rx = [re.compile(r"__pycache__")]
    exts = [".py"]

    # 2. ACT: Iterate through all results and measure time
    start_time = time.perf_counter()
    file_count = 0
    for file_metadata in scanner.yield_project_files(
            "/root", exts, include_rx, exclude_rx,
            process_modules=True, process_tests=True, process_resources=True
    ):
        if file_metadata["status"] == "process":
            file_count += 1

    duration = time.perf_counter() - start_time

    # 3. ASSERT: Performance and integrity
    assert file_count == total_files
    # Critical Point: Scanning 10k items in-memory should take < 1 second
    # even with regex overhead.
    assert duration < 1.0, f"Scanner too slow: {duration:.2f}s for {total_files} files"


def test_scanner_memory_efficiency_via_generator(mocker, scanner):
    # 1. ARRANGE: Mock a large directory
    mocker.patch("os.walk", return_value=[
        ("/root", [], [f"file_{i}.py" for i in range(5000)])
    ])

    # 2. ACT: Get the generator but don't consume it fully at once
    gen = scanner.yield_project_files(
        "/root", [".py"], [re.compile(r".*")], [], True, True, True
    )

    # 3. ASSERT: Verify it's an iterator (lazy loading)
    # This ensures we don't load 5000 dicts into memory until needed
    assert hasattr(gen, "__iter__")
    assert hasattr(gen, "__next__")

    first_item = next(gen)
    assert first_item["status"] == "process"


def test_scanner_resilience_to_deep_nesting(mocker, scanner):
    # 1. ARRANGE: Simulate a directory 30 levels deep
    deep_path = "/root/" + "/".join([f"level_{i}" for i in range(30)])
    mocker.patch("os.walk", return_value=[
        (deep_path, [], ["leaf.py"])
    ])
    mocker.patch("os.path.abspath", return_value=deep_path)
    # Mock relpath to simulate correct distance calculation
    mocker.patch("os.path.relpath", return_value="level_0/.../leaf.py")

    # 2. ACT
    files = list(scanner.yield_project_files(
        "/root", [".py"], [re.compile(r".*")], [], True, True, True
    ))

    # 3. ASSERT
    assert len(files) == 1
    assert files[0]["rel_path"] == "level_0/.../leaf.py"


def test_scanner_performance_under_complex_regex_load(mocker, scanner):
    # 1. ARRANGE: Create 50 complex exclusion patterns
    # This simulates a project with a very heavy .gitignore or custom rules
    complex_excludes = [re.compile(rf".*ignore_me_{i}.*/.*") for i in range(50)]

    mocker.patch("os.walk", return_value=[
        ("/root", [], ["valid.py", "ignore_me_25_file.tmp", "other.py"])
    ])

    # 2. ACT
    start_time = time.perf_counter()
    files = list(scanner.yield_project_files(
        "/root", [".py"], [re.compile(r".*")], complex_excludes, True, True, True
    ))
    duration = time.perf_counter() - start_time

    # 3. ASSERT
    # Ensure patterns are being applied correctly
    processed = [f for f in files if f["status"] == "process"]
    skipped = [f for f in files if f["status"] == "skipped"]

    assert len(processed) == 2
    assert len(skipped) == 1
    # Complex regex shouldn't cause dramatic slowdown for few files
    assert duration < 0.1