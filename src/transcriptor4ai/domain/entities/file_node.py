from __future__ import annotations

"""
Directory Tree Structure Data Models.

Provides the recursive type definitions and structural nodes used by
the static analysis subsystem to build hierarchical project maps.
"""

from dataclasses import dataclass
from typing import Dict, Union

# ==============================================================================
# DOMAIN ENTITIES
# ==============================================================================
@dataclass(frozen=True)
class FileNode:
    """
    Represents a leaf entry (file) in the directory tree.

    Attributes:
        path: Absolute filesystem path to the file.
    """
    path: str

# ==============================================================================
# TYPE DEFINITIONS
# ==============================================================================
# Recursive type definition for the directory tree structure
Tree = Dict[str, Union["Tree", FileNode]]