from __future__ import annotations

"""
Network Shared Utilities and Constants.

Defines global connection parameters (User-Agent, Timeouts) and cryptographic
helpers used across different API clients for integrity verification.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

# ==============================================================================
# NETWORK CONSTANTS
# ==============================================================================
USER_AGENT = "Transcriptor4AI-Client/2.1.0"
DEFAULT_TIMEOUT = 10  # Seconds
CHUNK_SIZE = 8192     # 8 KB buffer for streaming

# ==============================================================================
# INTEGRITY UTILITIES
# ==============================================================================
def calculate_sha256(file_path: str) -> str:
    """
    Compute SHA-256 digest for local file integrity verification.

    Used primarily to validate downloaded binaries against remote checksums
    before applying updates.

    Args:
        file_path: Absolute path to the target file.

    Returns:
        str: Hexadecimal representation of the SHA-256 hash.
             Returns an empty string if the file cannot be read.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read in chunks to avoid loading large files into memory
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    except OSError as e:
        logger.warning(f"NetworkCommon: Hashing failed for '{file_path}': {e}")
        return ""
    except Exception as e:
        logger.error(f"NetworkCommon: Unexpected error hashing '{file_path}': {e}")
        return ""