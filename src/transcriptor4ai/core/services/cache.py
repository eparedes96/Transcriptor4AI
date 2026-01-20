from __future__ import annotations

"""
Local Cache Persistence Service.

Provides a thread-safe, SQLite-backed caching mechanism to skip redundant
processing of files. Implements a composite hashing strategy (File Metadata +
Configuration Context) to ensure cache validity across session changes.
Now persists token counts to ensure cost estimation integrity on cache hits.
"""

import hashlib
import logging
import os
import sqlite3
import threading
import time
from typing import Optional, Tuple

from transcriptor4ai.infra.fs import get_user_data_dir

logger = logging.getLogger(__name__)


class CacheService:
    """
    Manages the persistent storage of processed file artifacts.

    Uses a local SQLite database to store results and metadata of
    processed files to optimize performance and cost estimation.
    """

    DB_FILENAME = "cache.db"

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
        Create the database table if it does not exist and handle migrations.
        """
        try:
            with self._lock:
                with sqlite3.connect(self._db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("PRAGMA journal_mode=WAL;")

                    # Create core table
                    cursor.execute("""
                        CREATE TABLE IF NOT EXISTS file_cache (
                            composite_hash TEXT PRIMARY KEY,
                            file_path TEXT,
                            content TEXT,
                            last_access REAL,
                            created_at REAL
                        )
                    """)

                    cursor.execute("PRAGMA table_info(file_cache)")
                    columns = [info[1] for info in cursor.fetchall()]
                    if "token_count" not in columns:
                        logger.info("CacheService: Migrating database to include token_count...")
                        sql_migration = (
                            "ALTER TABLE file_cache "
                            "ADD COLUMN token_count INTEGER DEFAULT 0"
                        )
                        cursor.execute(sql_migration)

                    conn.commit()
            logger.debug(f"CacheService: Database initialized at {self._db_path}")

        except sqlite3.Error as e:
            msg = f"CacheService: Initialization failure. Caching disabled. Error: {e}"
            logger.warning(msg)
            self._enabled = False

    def get_entry(self, composite_hash: str) -> Optional[Tuple[str, int]]:
        """
        Retrieve processed content and its token count from the cache.

        Args:
            composite_hash: Unique identifier for the file state.

        Returns:
            Optional[Tuple[str, int]]: (Content, TokenCount) or None on miss.
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
                        return str(row[0]), int(row[1] or 0)

            return None

        except sqlite3.Error as e:
            logger.warning(f"CacheService: Read error for hash {composite_hash[:8]}: {e}")
            return None

    def set_entry(
        self,
        composite_hash: str,
        file_path: str,
        content: str,
        token_count: int
    ) -> None:
        """
        Store or update a processed entry in the cache.

        Args:
            composite_hash: Unique identifier.
            file_path: Original file path.
            content: The processed string.
            token_count: Number of tokens calculated for this content.
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
            logger.warning(f"CacheService: Write error for {os.path.basename(file_path)}: {e}")

    def purge_all(self) -> None:
        """Clear all cached entries effectively resetting the storage."""
        if not self._enabled:
            return

        try:
            with self._lock:
                # Step 1: Clear all rows (Transactional)
                with sqlite3.connect(self._db_path) as conn:
                    conn.execute("DELETE FROM file_cache")

                # Step 2: Reclaim disk space (Non-transactional)
                conn = sqlite3.connect(self._db_path)
                conn.isolation_level = None
                try:
                    conn.execute("VACUUM")
                finally:
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
        """Generate a deterministic SHA-256 hash combining file state and configuration."""
        raw_key = f"{file_path}|{mtime}|{file_size}|{config_hash}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()