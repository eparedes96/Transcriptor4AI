from __future__ import annotations

import hashlib

USER_AGENT = "Transcriptor4AI-Client/2.1.0"
DEFAULT_TIMEOUT = 10
CHUNK_SIZE = 8192

def calculate_sha256(file_path: str) -> str:
    """Compute SHA-256 digest for local file integrity verification."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except Exception:
        return ""