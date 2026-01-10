from __future__ import annotations

"""
Code Minification Utility for Transcriptor4AI.

Reduces token consumption by removing non-essential characters, 
redundant comments (including inline comments), and excessive whitespace 
while maintaining code logic integrity.
"""

import logging
import re
from typing import Final

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Minification Patterns
# -----------------------------------------------------------------------------
_PYTHON_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"#.*")
_C_STYLE_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"//.*")
_MULTI_NEWLINE_PATTERN: Final[re.Pattern] = re.compile(r"\n{3,}")


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def minify_code(text: str, extension: str = ".py") -> str:
    """
    Remove comments and redundant whitespace from source code.

    Args:
        text: The raw source code content.
        extension: The file extension to determine comment style.

    Returns:
        Optimized string with a lower token count.
    """
    if not text:
        return ""

    original_len = len(text)

    # 1. Remove Line and Inline Comments based on extension
    ext_lower = extension.lower()

    if ext_lower in ('.py', '.yaml', '.yml', '.sh', '.bash'):
        text = _PYTHON_COMMENT_PATTERN.sub("", text)
    elif ext_lower in ('.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go'):
        text = _C_STYLE_COMMENT_PATTERN.sub("", text)

    # 2. Collapse excessive newlines (max 2 consecutive)
    text = _MULTI_NEWLINE_PATTERN.sub("\n\n", text)

    # 3. Strip trailing whitespace from each line (essential for inline comments)
    text = "\n".join(line.rstrip() for line in text.splitlines())

    # 4. Final trim
    text = text.strip()

    optimized_len = len(text)
    if original_len > 0:
        reduction = 100 - (optimized_len * 100 / original_len)
        logger.debug(f"Minified {extension}: {original_len} -> {optimized_len} chars ({reduction:.1f}% reduction)")

    return text