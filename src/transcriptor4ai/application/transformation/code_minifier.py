from __future__ import annotations

"""
Code Minification Service.

Provides non-destructive code optimization by removing non-essential 
characters such as comments and redundant whitespace. Uses context-aware 
regular expressions to ensure that symbols inside string literals (e.g., 
URLs with anchors or CSS hex colors) are never truncated.
"""

import logging
import re
from typing import Final, Iterator

logger = logging.getLogger(__name__)

# ==============================================================================
# MINIFICATION CONSTANTS (Context-Aware Patterns)
# ==============================================================================

# Pattern Logic:
# 1. Match double-quoted strings: "(?:\\.|[^"\\])*"
# 2. Match single-quoted strings: '(?:\\.|[^'\\])*'
# 3. Match comments: #.* (Python) or //.* (C-Style)
# Capturing group 1 holds the string literals to be preserved.

_PYTHON_MINIFY_RX: Final[re.Pattern] = re.compile(
    r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|#.*'
)

_C_STYLE_MINIFY_RX: Final[re.Pattern] = re.compile(
    r'("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')|//.*'
)


# ==============================================================================
# MINIFIER SERVICE IMPLEMENTATION
# ==============================================================================

class CodeMinifierService:
    """
    Application service responsible for reducing code density without
    altering execution logic or breaking string literals.
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

        # 1. PROCESS: Stream through the line-based engine
        line_iter = iter(text.splitlines(keepends=True))
        result = "".join(list(self.minify_stream(line_iter, extension)))

        # 2. METRICS: Performance analysis
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
        Identifies and protects string literals while stripping comments.

        Args:
            lines: Iterator yielding lines of code.
            extension: Target file extension for syntax-specific rules.

        Yields:
            str: Processed and optimized lines.
        """
        ext_lower = (extension or "").lower()
        empty_line_count = 0

        # Helper callback for re.sub:
        # If group 1 (string) matched, return it intact. Else (comment matched), return empty.
        def _selective_strip(match: re.Match) -> str:
            return match.group(1) if match.group(1) is not None else ""

        for line in lines:
            processed = line

            # 1. TRANSFORM: Strip comments with string-awareness
            if ext_lower in ('.py', '.yaml', '.yml', '.sh', '.bash'):
                processed = _PYTHON_MINIFY_RX.sub(_selective_strip, processed)
            elif ext_lower in (
                '.js', '.ts', '.jsx', '.tsx', '.java', '.c', '.cpp', '.h', '.hpp', '.cs', '.go'
            ):
                processed = _C_STYLE_MINIFY_RX.sub(_selective_strip, processed)

            # 2. CLEAN: Remove trailing horizontal whitespace
            processed = processed.rstrip()

            # 3. COLLAPSE: Vertical whitespace optimization (Max 1 empty line)
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

def minify_code(text: str, extension: str = ".py") -> str:
    """Legacy wrapper for CodeMinifierService.minify."""
    return CodeMinifierService().minify(text, extension)


def minify_code_stream(lines: Iterator[str], extension: str = ".py") -> Iterator[str]:
    """Legacy wrapper for CodeMinifierService.minify_stream."""
    return CodeMinifierService().minify_stream(lines, extension)