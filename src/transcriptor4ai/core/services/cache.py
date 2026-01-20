from __future__ import annotations

"""
Local Cache Persistence Service.

Provides a thread-safe, SQLite-backed caching mechanism to skip redundant
processing of files. Implements a composite hashing strategy (File Metadata +
Configuration Context) to ensure cache validity across session changes.
Designed to fail silently (Fail-Safe) to avoid blocking the main pipeline.
"""

import hashlib
import logging
import os
import sqlite3
import threading
import time
from typing import Optional

from transcriptor4ai.infra.fs import get_user_data_dir

logger = logging.getLogger(__name__)


class CacheService:
    """
    Manages the persistent storage of processed file artifacts.

    Uses a local SQLite database to store the result of CPU-intensive
    operations (minification, sanitization, tokenization).
    """

    DB_FILENAME = "cache.db"
    SCHEMA_VERSION = 1

    def __init__(self) -> None:
        """
        Initialize the cache service and ensure the database schema exists.
        """
        self._db_path = os.path.join(get_user_data_dir(), self.DB_FILENAME)
        self._lock = threading.Lock()
        self._enabled = True

        self._init_db()

    def _init_db(self) -> None:
        """
        Create the database table if it does not exist.
        """
        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    # WAL mode improves concurrency performance
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
                    conn.commit()
            logger.debug(f"CacheService: Database initialized at {self._db_path}")

        except sqlite3.Error as e:
            msg = f"CacheService: Failed to initialize database. Caching disabled. Error: {e}"
            logger.warning(msg)
            self._enabled = False

    def get_entry(self, composite_hash: str) -> Optional[str]:
        """
        Retrieve processed content from the cache if available.

        Args:
            composite_hash: Unique identifier for the file state + config context.

        Returns:
            Optional[str]: The cached content string, or None on miss/error.
        """
        if not self._enabled:
            return None

        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        "SELECT content FROM file_cache WHERE composite_hash = ?",
                        (composite_hash,)
                    )
                    row = cursor.fetchone()

                    if row:
                        return str(row[0])

            return None

        except sqlite3.Error as e:
            logger.warning(f"CacheService: Read error for hash {composite_hash[:8]}: {e}")
            return None

    def set_entry(self, composite_hash: str, file_path: str, content: str) -> None:
        """
        Store or update a processed entry in the cache.

        Args:
            composite_hash: Unique identifier.
            file_path: Original file path (for debugging/audit).
            content: The final processed string to store.
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
                        (composite_hash, file_path, content, last_access, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (composite_hash, file_path, content, now, now))
                    conn.commit()

        except sqlite3.Error as e:
            logger.warning(f"CacheService: Write error for {os.path.basename(file_path)}: {e}")

    def purge_all(self) -> None:
        """
        Clear all cached entries effectively resetting the storage.

        Executes VACUUM outside of the transaction block to reclaim disk space.
        """
        if not self._enabled:
            return

        try:
            with self._lock:
                conn = sqlite3.connect(self._db_path)
                # First delete all data and commit transaction
                conn.execute("DELETE FROM file_cache")
                conn.commit()
                # VACUUM must be executed outside of an active transaction
                conn.execute("VACUUM")
                conn.close()

            logger.info("CacheService: Storage successfully purged.")

        except sqlite3.Error as e:
            logger.error(f"CacheService: Failed to purge database: {e}")

    @staticmethod
    def compute_composite_hash(
        file_path: str,
        mtime: float,
        file_size: int,
        config_hash: str
    ) -> str:
        """
        Generate a deterministic SHA-256 hash combining file state and configuration.

        This ensures that if the file changes OR the configuration changes (e.g.,
        enabling comments or sanitization), the cache is automatically invalidated.

        Args:
            file_path: Absolute path of the file.
            mtime: Modification timestamp.
            file_size: Size in bytes.
            config_hash: A hash representing the current settings state.

        Returns:
            str: Hexadecimal SHA-256 hash string.
        """
        raw_key = f"{file_path}|{mtime}|{file_size}|{config_hash}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()