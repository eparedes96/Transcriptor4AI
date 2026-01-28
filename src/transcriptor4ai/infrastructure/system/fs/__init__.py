from __future__ import annotations

"""
FS Infrastructure Package Entry Point.

Exposes the primary FileSystemAdapter and the standalone shell utility.
Acts as the public interface for the filesystem infrastructure layer.
"""

# ==============================================================================
# PUBLIC API EXPOSURE
# ==============================================================================

# 1. CORE ADAPTER: Main entry point for dependency injection
from .adapter import FileSystemAdapter

# 2. SHELL UTILITIES: Exposed with alias to match previous API naming
from .shell_utils import open_file_explorer_cmd as open_file_explorer

# ==============================================================================
# PACKAGE MANIFEST
# ==============================================================================

# Defines the symbols available when using 'from fs import *'
__all__ = ["FileSystemAdapter", "open_file_explorer"]