from __future__ import annotations

from dataclasses import dataclass

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class TranscriptionError:
    """
    Represents an error encountered during file processing.

    Attributes:
        rel_path: Relative path of the file where the error occurred.
        error: Description or exception message.
    """
    rel_path: str
    error: str