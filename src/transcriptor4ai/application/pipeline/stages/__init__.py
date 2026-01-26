from __future__ import annotations

"""
Pipeline Stages Facade.

Exposes the sequential processing blocks used by the Orchestrator to 
execute the transcription workflow.
"""

from .assembler import assemble_and_finalize
from .setup import prepare_environment
from .transcriber import transcribe_code
from .validator import validate_config

__all__ = [
    "assemble_and_finalize",
    "prepare_environment",
    "transcribe_code",
    "validate_config",
]