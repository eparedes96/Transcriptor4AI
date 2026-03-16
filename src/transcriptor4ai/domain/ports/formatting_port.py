from __future__ import annotations

"""
Output Formatting Infrastructure Port.

Defines the contract for polymorphic context rendering. Implementations 
of this port (Strategies) are responsible for translating domain content 
into specific structural schemas (XML, Markdown, PlainText) required 
by different LLM providers.
"""

from abc import ABC, abstractmethod


# ==============================================================================
# FORMATTING INTERFACE (PORT)
# ==============================================================================

class IOutputFormatter(ABC):
    """
    Abstract Base Class defining the blueprint for context formatters.

    This interface ensures that the transcription pipeline can generate
    diverse output structures without knowing the specific implementation
    details of the target format.
    """

    @abstractmethod
    def get_extension(self) -> str:
        """
        Returns the standard file extension for this format.

        Returns:
            str: Extension including the leading dot (e.g., '.xml', '.md').
        """
        pass

    @abstractmethod
    def render_header(self, title: str) -> str:
        """
        Generates the opening sequence of the context document.

        Args:
            title: The project or session title.
        """
        pass

    @abstractmethod
    def render_preamble(self, text: str) -> str:
        """
        Formats the custom system prompt or instructions (Preamble).

        Args:
            text: Raw instruction string provided by the user.
        """
        pass

    @abstractmethod
    def render_tree(self, lines: list[str]) -> str:
        """
        Wraps the ASCII directory tree in format-specific tags or blocks.

        Args:
            lines: List of strings representing the directory structure.
        """
        pass

    @abstractmethod
    def render_section_divider(self, section_name: str) -> str:
        """
        Creates a visual or structural separation between content categories.

        Args:
            section_name: Identifier of the section (e.g., 'TESTS').
        """
        pass

    @abstractmethod
    def render_file_block(self, rel_path: str, content: str) -> str:
        """
        Encapsulates a single file's content with its metadata.

        Args:
            rel_path: Project-relative path of the file.
            content: The processed (minified/sanitized) source code.
        """
        pass

    @abstractmethod
    def render_footer(self) -> str:
        """
        Generates the closing sequence of the context document.
        """
        pass