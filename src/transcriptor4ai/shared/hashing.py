from __future__ import annotations

"""
Cryptographic Fingerprinting and Integrity Service.

Provides deterministic hashing utilities to ensure file integrity during 
updates and unique state identification for the caching engine. 
Centralizes hashing logic to maintain architectural purity across layers.
"""

import hashlib
import logging

# Standardized logger for the shared domain
logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API: INTEGRITY & IDENTIFICATION
# ==============================================================================

def calculate_sha256(file_path: str) -> str:
    """
    Compute a SHA-256 digest for a local file using buffered streaming.

    Optimized for memory efficiency by processing files in fixed-size chunks,
    preventing large binary artifacts from exhausting system RAM.

    Args:
        file_path: Absolute filesystem path to the target file.

    Returns:
        str: Hexadecimal representation of the SHA-256 hash or empty string on error.
    """
    sha256_hash = hashlib.sha256()

    try:
        # 1. I/O OPERATION: Open file in binary read mode
        with open(file_path, "rb") as f:

            # 2. STREAMING: Read by blocks to optimize memory footprint
            # Using 4096 bytes as standard sector-aligned buffer size
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        # 3. OUTPUT: Generate the final hexadecimal digest
        return sha256_hash.hexdigest()

    except OSError as e:
        logger.warning(f"IntegrityCheck: Hashing failed for '{file_path}': {e}")
        return ""


def compute_composite_hash(
        file_path: str,
        mtime: float,
        file_size: int,
        config_hash: str
) -> str:
    """
    Generate a deterministic identity key for the pipeline caching engine.

    Combines physical file metadata with current transformation settings
    to detect if a re-transcription is required.

    Args:
        file_path: Absolute path identifier of the source file.
        mtime: Last modification timestamp from the OS.
        file_size: Physical file size in bytes.
        config_hash: Unique fingerprint of the active transformation settings.

    Returns:
        str: A 64-character SHA-256 hex string representing the unique state.
    """
    # 1. KEY FORMATION: Create a reproducible state string
    # Using pipe separators to prevent key collision attacks
    raw_key = f"{file_path}|{mtime}|{file_size}|{config_hash}"

    # 2. ENCODING: Transform state string into UTF-8 bytes for hashing
    encoded_key = raw_key.encode("utf-8")

    # 3. COMPRESSION: Generate the unique identity fingerprint
    return hashlib.sha256(encoded_key).hexdigest()