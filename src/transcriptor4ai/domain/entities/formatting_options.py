from __future__ import annotations

"""
Formatting Domain Options and Enumerations.

Defines the strictly typed constants and enumerations used to govern 
the polymorphic output system. These definitions act as the ground 
truth for the Strategy Pattern implementation in the application layer.
"""

from enum import Enum, unique


# ==============================================================================
# OUTPUT STRATEGY ENUMERATIONS
# ==============================================================================

@unique
class OutputFormat(Enum):
    """
    Supported architectural formats for LLM context generation.

    Attributes:
        PLAIN_TEXT: Standard text format with line separators (v2.1 legacy).
        MARKDOWN: Document structure using blocks and syntax highlighting.
        XML: Hierarchical tags (<document>, <file>) optimized for Claude/Anthropic.
    """
    PLAIN_TEXT = "plaintext"
    MARKDOWN = "markdown"
    XML = "xml"

    @classmethod
    def list_values(cls) -> list[str]:
        """Returns a list of all raw string values for UI population."""
        return [item.value for item in cls]

    @classmethod
    def from_str(cls, value: str, fallback: OutputFormat | None = None) -> OutputFormat:
        """
        Safe factory method to instantiate from raw strings.

        Uses Late Binding for the default fallback to ensure that the
        returned object is always a member of the Enum class and not
         the primitive string assigned during class definition.

        Args:
            value: Raw string from config or UI.
            fallback: Default Enum member if input is unrecognized.

        Returns:
            OutputFormat: The matched Enum member or the designated fallback.
        """
        # 1. VALIDATION: Handle potential null/empty inputs
        if not isinstance(value, str):
            return fallback if fallback is not None else cls.PLAIN_TEXT

        # 2. RESOLUTION: Attempt to map string to Enum member
        try:
            return cls(value.strip().lower())
        except (ValueError, AttributeError):
            # 3. FALLBACK: Return late-bound PLAIN_TEXT member if no specific fallback provided
            return fallback if fallback is not None else cls.PLAIN_TEXT


# ==============================================================================
# CONTENT CLASSIFICATION ENUMERATIONS
# ==============================================================================

class ContextSection(Enum):
    """Identifies the semantic sections within a unified context file."""
    PREAMBLE = "PREAMBLE"
    TREE = "DIRECTORY_TREE"
    MODULES = "SCRIPTS_MODULES"
    TESTS = "TEST_SUITE"
    RESOURCES = "PROJECT_RESOURCES"