from __future__ import annotations

"""
Code Minification Utility for Transcriptor4AI.

Reduces token consumption by removing non-essential characters and comments.
Supports stateful streaming, allowing the collapse of multi-line newlines without loading the whole file into memory.
"""

import logging
import re
from typing import Final, Iterator

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Minification Patterns
# -----------------------------------------------------------------------------
_PYTHON_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"#.*")
_C_STYLE_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"//.*")


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def minify_code(text: str, extension: str = ".py") -> str:
    """
    Standard string-based minification.
    Maintained for backward compatibility.
    """
    if not text:
        return ""

    original_len = len(text)
    result = "".join(list(minify_code_stream(text.splitlines(keepends=True), extension)))

    optimized_len = len(result)
    if original_len > 0:
        reduction = 100 - (optimized_len * 100 / original_len)
        logger.debug(f"Minified {extension}: {original_len} -> {optimized_len} chars ({reduction:.1f}% reduction)")

    return result.strip()


# -----------------------------------------------------------------------------
# Public API
# -----------------------------------------------------------------------------

def minify_code_stream(lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
    """
    Stream-based minification. Performs line-by-line comment removal
    and stateful newline collapsing.

    Args:
        lines: An iterator of raw code lines.
        extension: File extension to determine comment style.

    Yields:
        Optimized code lines.
    """
    ext_lower = (extension or "").lower()
    empty_line_count = 0

    for line in lines:
        processed = line

        # 1. Remove Line and Inline Comments
        if ext_lower in ('.py', '.yaml', '.yml', '.sh', '.bash'):
            processed = _PYTHON_COMMENT_PATTERN.sub("", processed)
        elif ext_lower in ('.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go'):
            processed = _C_STYLE_COMMENT_PATTERN.sub("", processed)

        # 2. Strip trailing whitespace
        processed = processed.rstrip()

        # 3. Stateful Newline Collapsing (Max 1 empty line between content)
        if not processed:
            empty_line_count += 1
            if empty_line_count == 1:
                yield "\n"
        else:
            empty_line_count = 0
            yield processed + "\n"