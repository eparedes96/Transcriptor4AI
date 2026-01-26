from __future__ import annotations

"""
Pipeline Package.

This package contains the core execution engine of Transcriptor4AI, 
implementing the high-level orchestration of scanning, transcription, 
and context assembly.
"""

from .orchestrator import run_pipeline

__all__ = [
    "run_pipeline",
]