from __future__ import annotations

"""
Pipeline Components Facade.

Provides low-level utilities for file system interaction and stream 
processing within the transcription pipeline.
"""

from transcriptor4ai.application.common.file_filters import (
    compile_patterns,
    is_resource_file,
    is_test,
    matches_any,
    matches_include,
)
from .file_reader import stream_file_content
from .file_writer import append_entry, initialize_output_file

__all__ = [
    "compile_patterns",
    "is_resource_file",
    "is_test",
    "matches_any",
    "matches_include",
    "stream_file_content",
    "append_entry",
    "initialize_output_file",
]