from __future__ import annotations

"""
Code Minification Utility.

Reduces token consumption by removing non-essential characters (comments,
whitespace) while preserving code logic. Supports stateful streaming to
collapse multiple empty lines efficiently.
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
    Minify a full string of code in memory.

    Args:
        text: The raw source code.
        extension: The file extension to determine comment syntax.

    Returns:
        str: The minified code string.
    """
    if not text:
        return ""

    original_len = len(text)
    result = "".join(list(minify_code_stream(text.splitlines(keepends=True), extension)))

    optimized_len = len(result)
    if original_len > 0:
        reduction = 100 - (optimized_len * 100 / original_len)
        logger.debug(f"Minified {extension}: {original_len} -> {optimized_len} chars ({reduction:.1f}% reduction)")

    # Use rstrip() instead of strip() to preserve leading indentation of the first line
    return result.rstrip()


def minify_code_stream(lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
    """
    Minify code line-by-line.
    Performs comment removal and collapses consecutive empty lines.

    Args:
        lines: An iterator yielding lines of code.
        extension: The file extension to determine comment syntax.

    Yields:
        str: Optimized code lines.
    """
    ext_lower = (extension or "").lower()
    empty_line_count = 0

    for line in lines:
        processed = line

        # 1. Remove Line and Inline Comments based on language
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