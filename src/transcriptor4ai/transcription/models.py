from __future__ import annotations

from dataclasses import dataclass

# -----------------------------------------------------------------------------
# Modelo de error
# -----------------------------------------------------------------------------
@dataclass
class TranscriptionError:
    rel_path: str
    error: str