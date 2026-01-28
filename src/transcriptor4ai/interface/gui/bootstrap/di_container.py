from __future__ import annotations

"""
Application Dependency Injection Container.

Provides a centralized factory to instantiate infrastructure adapters, 
initialize repositories, and recover persistent application state. It creates 
 the 'ApplicationContext' required to bootstrap the GUI controllers.
"""

import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List

from transcriptor4ai.domain.entities import app_config as domain_cfg
from transcriptor4ai.infrastructure.network.github_release_client import GithubReleaseClient
from transcriptor4ai.infrastructure.persistence.json_config_repo import JsonConfigRepository
from transcriptor4ai.infrastructure.persistence.model_registry_repo import ModelRegistryRepository
from transcriptor4ai.infrastructure.persistence.sqlite_cache_repo import SqliteCacheRepository
from transcriptor4ai.infrastructure.system.fs.adapter import FileSystemAdapter
from transcriptor4ai.infrastructure.system.user_context_adapter import UserContextAdapter

# Standardized infrastructure logger
logger = logging.getLogger(__name__)


# ==============================================================================
# DATA MODELS
# ==============================================================================

@dataclass(frozen=True)
class ApplicationContext:
    """
    Immutable container for initialized application services and state.
    """
    config: Dict[str, Any]
    app_state: Dict[str, Any]
    profile_names: List[str]

    # Adapters (Ports)
    fs: FileSystemAdapter
    cache: SqliteCacheRepository
    config_repo: JsonConfigRepository
    registry: ModelRegistryRepository
    user_context: UserContextAdapter
    network: GithubReleaseClient


# ==============================================================================
# CONTEXT FACTORY
# ==============================================================================

def build_application_context() -> ApplicationContext:
    """
    Execute the cold-start initialization sequence for all system components.

    Returns:
        ApplicationContext: A fully-wired dependency graph and initial state.
    """
    logger.info("DIContainer: Orchestrating infrastructure initialization...")

    # 1. ADAPTER INSTANTIATION: Create technical adapters
    fs = FileSystemAdapter()
    user_context = UserContextAdapter()
    network = GithubReleaseClient()

    config_repo = JsonConfigRepository(fs)
    cache = SqliteCacheRepository(fs)
    registry = ModelRegistryRepository(fs)

    # 2. STATE RECOVERY: Load data from persistent storage
    try:
        app_state = config_repo.load_app_state()
        config = config_repo.load_config()

        # Extract existing profile identifiers
        saved_profiles = app_state.get("saved_profiles", {})
        profile_names = sorted(list(saved_profiles.keys()))

        logger.debug(f"DIContainer: State recovered ({len(profile_names)} profiles found).")

    except Exception as e:
        # CRITICAL FALLBACK: If persistence is corrupted, reset to safe defaults
        logger.error(f"DIContainer: Critical state failure: {e}. Falling back to defaults.")

        cwd = os.getcwd()
        app_state = domain_cfg.get_default_app_state(cwd)
        config = domain_cfg.get_default_config(cwd)
        profile_names = []

    # 3. CONTEXT ASSEMBLY: Return the DTO
    return ApplicationContext(
        config=config,
        app_state=app_state,
        profile_names=profile_names,
        fs=fs,
        cache=cache,
        config_repo=config_repo,
        registry=registry,
        user_context=user_context,
        network=network
    )