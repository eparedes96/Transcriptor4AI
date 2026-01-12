from __future__ import annotations

"""
Tree Structure Data Models.

Defines the recursive types used to represent the directory structure
analysis results.
"""

from dataclasses import dataclass
from typing import Dict, Union


@dataclass(frozen=True)
class FileNode:
    """
    Represents a leaf node (file) in the directory tree structure.

    Attributes:
        path: Absolute path to the file on the filesystem.
    """
    path: str


# Recursive type alias for the directory tree structure
Tree = Dict[str, Union["Tree", FileNode]]