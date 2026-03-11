from __future__ import annotations

"""
Global Pytest Configuration and Shared Fixtures.

Defines common data structures, domain entity factories, and infrastructure 
mocks for the Transcriptor4AI testing suite. Ensures isolation from 
external systems (I/O, Network, OS) for Unit Tests.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pytest

# ==============================================================================
# CONFIGURATION FIXTURES (DOMAIN ENTITIES)
# ==============================================================================

@pytest.fixture
def mock_config_dict() -> Dict[str, Any]:
    """
    Returns a complete and valid configuration dictionary for v2.1.

    Reflects the domain entity structure used in the pipeline and
    configuration repositories. Acts as the 'Happy Path' config state.
    """
    return {
        # Path Configuration
        "input_path": "/tmp/fake_project",
        "output_base_dir": "/tmp/output",
        "output_subdir_name": "transcript",
        "output_prefix": "test_prefix",

        # Processing Logic
        "processing_depth": "full",  # Options: "full", "skeleton", "tree_only"
        "process_modules": True,
        "process_tests": True,
        "process_resources": False,

        # Output Strategies
        "create_individual_files": True,
        "create_unified_file": True,

        # Filters & Regex
        "extensions": [".py", ".js"],
        "include_patterns": [".*"],
        "exclude_patterns": [r"__pycache__", r"\.git"],
        "respect_gitignore": True,

        # AI & Economic Metrics
        "target_model": "gpt-4o",

        # Static Analysis (AST)
        "generate_tree": True,
        "show_functions": False,
        "show_classes": False,
        "show_methods": False,
        "print_tree": False,

        # Optimization & Privacy
        "enable_sanitizer": False,
        "mask_user_paths": False,
        "minify_output": False,

        # Logging & Diagnostics
        "save_error_log": True
    }


@pytest.fixture
def mock_app_state(mock_config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulates the global application state structure (config.json).
    Used for testing persistence and migration layers.
    """
    return {
        "version": "2.1.0",
        "app_settings": {
            "theme": "System",
            "locale": "en",
            "allow_telemetry": False,
            "auto_check_updates": False
        },
        "last_session": mock_config_dict,
        "saved_profiles": {
            "Default": mock_config_dict
        },
        "custom_stacks": {}
    }


# ==============================================================================
# INFRASTRUCTURE MOCKS (PORTS)
# ==============================================================================

@pytest.fixture
def mock_user_context(mocker: Any) -> Any:
    """
    Mock for the IUserContext port to provide deterministic paths
    regardless of the OS running the tests (Linux/Windows parity).
    """
    mock = mocker.Mock()
    mock.get_username.return_value = "test_user"
    mock.get_home_directory.return_value = "/home/test_user"
    mock.get_context_info.return_value = {
        "username": "test_user",
        "home_dir": "/home/test_user"
    }
    return mock


@pytest.fixture
def mock_fs(mocker: Any) -> Any:
    """
    Mock for the IFileSystem port.
    Useful for unit tests that need to bypass physical I/O completely.
    For tests requiring real files, use the 'tmp_path' fixture instead.
    """
    mock = mocker.Mock()
    # Default behaviors to avoid TypeErrors in consumers
    mock.normalize_path.side_effect = lambda p, f: p if p else f
    mock.get_user_data_dir.return_value = "/mock/user/data"
    mock.check_existing_output_files.return_value = []
    mock.directory_exists.return_value = True
    return mock


@pytest.fixture
def memory_cache_repo() -> Any:
    """
    In-Memory implementation of ICacheRepository.

    Provides a fast, volatile storage for unit tests to verify caching logic
    without touching SQLite or the disk.
    """

    class MemoryCacheRepository:
        def __init__(self) -> None:
            self.store: Dict[str, Tuple[str, int]] = {}
            self.enabled = True

        def get_entry(self, composite_hash: str) -> Optional[Tuple[str, int]]:
            return self.store.get(composite_hash)

        def set_entry(self, composite_hash: str, file_path: str, content: str, token_count: int) -> None:
            self.store[composite_hash] = (content, token_count)

        def purge_all(self) -> None:
            self.store.clear()

        def is_enabled(self) -> bool:
            return self.enabled

    return MemoryCacheRepository()


@pytest.fixture
def mock_tokenizer_service(mocker: Any) -> Any:
    """
    Mock for the TokenizerService.

    Returns deterministic token counts based on string length (heuristic)
    to avoid importing heavy libraries (tiktoken) or making API calls during Unit Tests.
    """
    mock = mocker.Mock()

    # Simple deterministic formula: 1 token ~= 4 chars
    # Avoids returning 0 for short non-empty strings to prevent logic errors
    def fake_count(text: str, model: str = "") -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    mock.count.side_effect = fake_count
    return mock


# ==============================================================================
# PATHS & ASSETS (INTEGRATION HELPERS)
# ==============================================================================

@pytest.fixture(scope="session")
def static_assets_path() -> Path:
    """
    Resolves the absolute path to the static test data directory.
    This fixture ensures consistency regardless of where pytest is invoked.

    Returns:
        Path: The absolute path to 'tests/data'.
    """
    # Assumes conftest.py is located directly inside 'tests/'
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def sample_project_source(static_assets_path: Path) -> Path:
    """
    Shortcut to the 'sample_project' ground-truth directory.
    Use this source to copy files into 'tmp_path' for destructive tests.
    """
    return static_assets_path / "sample_project"