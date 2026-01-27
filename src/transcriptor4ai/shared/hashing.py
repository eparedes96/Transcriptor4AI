from __future__ import annotations

"""
Shared Hashing Utilities.

Provides deterministic fingerprinting for file integrity and cache identity.
Centralizing these functions ensures that both Application and Infrastructure
layers use consistent logic without direct coupling.
"""

import hashlib
import logging

logger = logging.getLogger(__name__)


# ==============================================================================
# PUBLIC API
# ==============================================================================

def calculate_sha256(file_path: str) -> str:
    """
    Compute SHA-256 digest for local file integrity verification.

    Args:
        file_path: Absolute path to the target file.

    Returns:
        str: Hexadecimal representation of the SHA-256 hash or empty string on error.
    """
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # 1. PROCESAMIENTO: Lectura por bloques para optimizar memoria
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()

    except OSError as e:
        logger.warning(f"Hashing failed for '{file_path}': {e}")
        return ""


def compute_composite_hash(
        file_path: str,
        mtime: float,
        file_size: int,
        config_hash: str
) -> str:
    """
    Generate a deterministic identity key for the caching engine.

    Args:
        file_path: Absolute path identifier.
        mtime: Last modification timestamp.
        file_size: Size in bytes.
        config_hash: Fingerprint of the current transformation settings.

    Returns:
        str: A 64-character hex string representing the state.
    """
    # 1. VALIDACIÓN: Asegurar que los componentes de entrada formen una clave única
    raw_key = f"{file_path}|{mtime}|{file_size}|{config_hash}"

    # 2. RETORNO: Hash SHA-256 de la cadena de estado
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()