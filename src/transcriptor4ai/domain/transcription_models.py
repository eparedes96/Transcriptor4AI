from __future__ import annotations

"""
Transcription Data Models.

Defines Data Transfer Objects (DTOs) related to file processing errors
and results within the transcription domain.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionError:
    """
    Represents an error encountered during the processing of a single file.

    Attributes:
        rel_path: The file path relative to the input root.
        error: Description of the error or exception message.
    """
    rel_path: str
    error: str