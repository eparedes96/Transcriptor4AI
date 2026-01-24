from __future__ import annotations

"""
Code Minification Service.

Provides non-destructive code optimization by removing non-essential 
characters such as comments and redundant whitespace. Implements a 
stateful streaming approach to collapse consecutive empty lines, 
optimizing token consumption for Large Language Model contexts.
"""

import logging
import re
from typing import Final, Iterator

logger = logging.getLogger(__name__)

# ==============================================================================
# MINIFICATION CONSTANTS
# ==============================================================================

_PYTHON_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"#.*")
_C_STYLE_COMMENT_PATTERN: Final[re.Pattern] = re.compile(r"//.*")


# ==============================================================================
# MINIFIER SERVICE IMPLEMENTATION
# ==============================================================================

class CodeMinifierService:
    """
    Application service responsible for reducing code density without
    altering execution logic.
    """

    def minify(self, text: str, extension: str = ".py") -> str:
        """
        Minify a full string of source code in-memory.

        Args:
            text: Raw source code content.
            extension: File extension to determine language-specific syntax.

        Returns:
            str: Minified source code.
        """
        if not text:
            return ""

        original_len = len(text)

        # 1. PROCESS: Use the streaming engine to maintain transformation consistency
        line_iter = iter(text.splitlines(keepends=True))
        result = "".join(list(self.minify_stream(line_iter, extension)))

        # 2. METRICS: Calculate and log compression efficiency
        optimized_len = len(result)
        if original_len > 0:
            reduction = 100 - (optimized_len * 100 / original_len)
            logger.debug(
                f"Minifier: {extension} | {original_len} -> {optimized_len} "
                f"chars ({reduction:.1f}% reduction)"
            )

        # Preserve leading indentation but remove trailing global artifacts
        return result.rstrip()

    def minify_stream(self, lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
        """
        Apply minification transformations to a line-based stream.

        Args:
            lines: Iterator yielding lines of code.
            extension: Target file extension for syntax-specific rules.

        Yields:
            str: Processed and optimized lines.
        """
        ext_lower = (extension or "").lower()
        empty_line_count = 0

        for line in lines:
            processed = line

            # 1. TRANSFORM: Strip comments based on file type
            if ext_lower in ('.py', '.yaml', '.yml', '.sh', '.bash'):
                processed = _PYTHON_COMMENT_PATTERN.sub("", processed)
            elif ext_lower in (
                '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go'
            ):
                processed = _C_STYLE_COMMENT_PATTERN.sub("", processed)

            # 2. CLEAN: Remove trailing horizontal whitespace
            processed = processed.rstrip()

            # 3. COLLAPSE: Stateful vertical whitespace optimization
            # Prevents LLM context waste by allowing maximum one consecutive newline
            if not processed:
                empty_line_count += 1
                if empty_line_count == 1:
                    yield "\n"
            else:
                empty_line_count = 0
                yield processed + "\n"

# ==============================================================================
# LEGACY COMPATIBILITY SHIMS
# ==============================================================================
# These functions provide backward compatibility with the existing pipeline
# until the orchestrator is refactored for full dependency injection.

def minify_code(text: str, extension: str = ".py") -> str:
    """Legacy wrapper for CodeMinifierService.minify."""
    return CodeMinifierService().minify(text, extension)


def minify_code_stream(lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
    """Legacy wrapper for CodeMinifierService.minify_stream."""
    return CodeMinifierService().minify_stream(lines, extension)