from __future__ import annotations

"""
SQLite Cache Repository.

Concrete implementation of the ICacheRepository port. Provides a thread-safe,
persistent caching mechanism using a local SQLite database file.

Features:
- Composite hashing for precise cache invalidation.
- ACID compliance via SQLite transactions.
- Automatic schema migration (v2.0 -> v2.1 token_count).
- Resilience against database corruption (automatic disablement).
"""

import hashlib
import logging
import os
import sqlite3
import threading
import time
from typing import Optional, Tuple

from transcriptor4ai.domain.ports.cache_port import ICacheRepository
from transcriptor4ai.infrastructure.system.os_file_system import FileSystemAdapter

logger = logging.getLogger(__name__)


# ==============================================================================
# SQLITE REPOSITORY IMPLEMENTATION
# ==============================================================================
class SqliteCacheRepository(ICacheRepository):
    """
    Persistence adapter using a local SQLite database.
    """

    DB_FILENAME = "cache.db"

    def __init__(self, fs_adapter: Optional[FileSystemAdapter] = None) -> None:
        """
        Initialize the repository and ensure schema integrity.

        Args:
            fs_adapter: FileSystem provider to resolve the user data directory.
        """
        self._fs = fs_adapter or FileSystemAdapter()
        self._db_path = os.path.join(self._fs.get_user_data_dir(), self.DB_FILENAME)
        self._lock = threading.Lock()
        self._enabled = True

        self._init_db()

    def is_enabled(self) -> bool:
        """Check if the database connection is operational."""
        return self._enabled

    # ==========================================================================
    # INITIALIZATION & MIGRATIONS
    # ==========================================================================
    def _init_db(self) -> None:
        """
        Bootstrap the database: create table and apply schema migrations.
        """
        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    # Enable Write-Ahead Logging for concurrency performance
                    cursor.execute("PRAGMA journal_mode=WAL;")

                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS file_cache (
                            composite_hash TEXT PRIMARY KEY,
                            file_path TEXT,
                            content TEXT,
                            last_access REAL,
                            created_at REAL
                        )
                    """)

                    # 1. MIGRATION CHECK: Schema v2.1 (Token Count)
                    cursor.execute("PRAGMA table_info(file_cache)")
                    columns = [info[1] for info in cursor.fetchall()]

                    if "token_count" not in columns:
                        logger.info("SqliteCache: Migrating schema to include token_count...")
                        sql_migration = (
                            "ALTER TABLE file_cache "
                            "ADD COLUMN token_count INTEGER DEFAULT 0"
                        )
                        cursor.execute(sql_migration)

                    conn.commit()

            logger.debug(f"SqliteCache: Initialized at {self._db_path}")

        except sqlite3.Error as e:
            msg = f"SqliteCache: Initialization failure. Caching disabled. Error: {e}"
            logger.warning(msg)
            self._enabled = False

    # ==========================================================================
    # CRUD OPERATIONS
    # ==========================================================================
    def get_entry(self, composite_hash: str) -> Optional[Tuple[str, int]]:
        """
        Retrieve cached content and metrics.
        """
        if not self._enabled:
            return None

        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT content, token_count FROM file_cache WHERE composite_hash = ?",
                        (composite_hash,)
                    )
                    row = cursor.fetchone()

                    if row:
                        # Return tuple: (processed_content, token_count)
                        return str(row[0]), int(row[1] or 0)

            return None

        except sqlite3.Error as e:
            logger.warning(f"SqliteCache: Read error for hash {composite_hash[:8]}: {e}")
            return None

    def set_entry(
            self,
            composite_hash: str,
            file_path: str,
            content: str,
            token_count: int
    ) -> None:
        """
        Upsert a cache entry with atomic transaction.
        """
        if not self._enabled:
            return

        now = time.time()
        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT OR REPLACE INTO file_cache 
                        (composite_hash, file_path, content, token_count, last_access, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (composite_hash, file_path, content, token_count, now, now))
                    conn.commit()

        except sqlite3.Error as e:
            logger.warning(f"SqliteCache: Write error for {os.path.basename(file_path)}: {e}")

    def purge_all(self) -> None:
        """
        Truncate the cache table and reclaim disk space.
        """
        if not self._enabled:
            return

        try:
            with self._lock:
                # 1. PROCESS: Transactional Delete
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("DELETE FROM file_cache")

                # 2. PROCESS: Vacuum (must be outside transaction block in some drivers)
                conn = sqlite3.connect(self._db_path)
                conn.isolation_level = None  # Autocommit mode for VACUUM
                try:
                    conn.execute("VACUUM")
                finally:
                    conn.close()

            logger.info("SqliteCache: Storage successfully purged.")

        except sqlite3.Error as e:
            logger.error(f"SqliteCache: Failed to purge database: {e}")

    # ==========================================================================
    # UTILITIES
    # ==========================================================================
    @staticmethod
    def compute_composite_hash(
            file_path: str,
            mtime: float,
            file_size: int,
            config_hash: str
    ) -> str:
        """
        Helper to generate the SHA-256 identity key.
        Note: This is a static utility provided by the repo for convenience,
        used by the pipeline before calling get/set.
        """
        raw_key = f"{file_path}|{mtime}|{file_size}|{config_hash}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()