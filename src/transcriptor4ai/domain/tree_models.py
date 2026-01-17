from __future__ import annotations

"""
Directory Tree Structure Data Models.

Provides the recursive type definitions and structural nodes used by 
the static analysis subsystem to build hierarchical project maps.
"""

from dataclasses import dataclass
from typing import Dict, Union

# -----------------------------------------------------------------------------
# STRUCTURAL COMPONENTS
# -----------------------------------------------------------------------------

@dataclass(frozen=True)
class FileNode:
    """
    Represents a leaf entry (file) in the directory tree.

    Attributes:
        path: Absolute filesystem path to the file.
    """
    path: str

Tree = Dict[str, Union["Tree", FileNode]]