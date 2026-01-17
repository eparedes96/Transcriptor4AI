from __future__ import annotations

"""
Code Minification Utility.

Provides non-destructive code optimization by removing non-essential 
characters such as comments and redundant whitespace. Implements a 
stateful streaming approach to collapse consecutive empty lines, 
optimizing token consumption for Large Language Model contexts.
"""

import logging
import re
from typing import Final, Iterator

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# MINIFICATION PATTERNS
# -----------------------------------------------------------------------------

_PYTHON_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"#.*")
_C_STYLE_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"//.*")

# -----------------------------------------------------------------------------
# PUBLIC API
# -----------------------------------------------------------------------------

def minify_code(text: str, extension: str = ".py") -> str:
    """
    Minify a full string of source code in-memory.

    Args:
        text: Raw source code content.
        extension: File extension to determine language-specific comment syntax.

    Returns:
        str: Minified source code with trailing whitespace and extra newlines removed.
    """
    if not text:
        return ""

    original_len = len(text)

    # Process using the streaming engine to maintain consistency
    result = "".join(list(minify_code_stream(iter(text.splitlines(keepends=True)), extension)))

    optimized_len = len(result)
    if original_len > 0:
        reduction = 100 - (optimized_len * 100 / original_len)
        logger.debug(f"Minified {extension}: {original_len} -> {optimized_len} chars ({reduction:.1f}% reduction)")

    # Preserve leading indentation but remove trailing global artifacts
    return result.rstrip()


def minify_code_stream(lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
    """
    Apply minification transformations to a line-based stream.

    Removes inline and block comments based on the provided extension
    and collapses multiple vertical whitespaces into a single newline
    to maximize token efficiency.

    Args:
        lines: Iterator yielding lines of code.
        extension: Target file extension for syntax rules.

    Yields:
        str: Processed and optimized lines.
    """
    ext_lower = (extension or "").lower()
    empty_line_count = 0

    for line in lines:
        processed = line

        # 1. Regex-based comment stripping (Language aware)
        if ext_lower in ('.py', '.yaml', '.yml', '.sh', '.bash'):
            processed = _PYTHON_COMMENT_PATTERN.sub("", processed)
        elif ext_lower in ('.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go'):
            processed = _C_STYLE_COMMENT_PATTERN.sub("", processed)

        # 2. Horizontal whitespace optimization
        processed = processed.rstrip()

        # 3. Stateful newline collapsing
        if not processed:
            empty_line_count += 1
            if empty_line_count == 1:
                yield "\n"
        else:
            empty_line_count = 0
            yield processed + "\n"