from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Union

# -----------------------------------------------------------------------------
# Modelo de datos
# -----------------------------------------------------------------------------
@dataclass(frozen=True)
class FileNode:
    path: str


Tree = Dict[str, Union["Tree", FileNode]]