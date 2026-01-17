from __future__ import annotations

"""
Transcription Domain Data Models.

Defines the Data Transfer Objects (DTOs) used to encapsulate atomic 
transcription units and error reporting within the processing domain.
"""

from dataclasses import dataclass

# -----------------------------------------------------------------------------
# ERROR TRACKING MODELS
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class TranscriptionError:
    """
    Encapsulates technical failure details during file processing.

    Attributes:
        rel_path: File path identifier relative to project root.
        error: Descriptive exception or error message.
    """
    rel_path: str
    error: str