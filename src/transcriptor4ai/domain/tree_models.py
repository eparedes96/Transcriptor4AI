from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Union

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class FileNode:
    """
    Represents a leaf node (file) in the directory tree.
    """
    path: str


# Recursive type definition for the directory tree structure
# Keys are filenames/dirnames, Values are either sub-trees (Dict) or leaf nodes (FileNode)
Tree = Dict[str, Union["Tree", FileNode]]