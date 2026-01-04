from __future__ import annotations

"""
Internationalization (i18n) utility for transcriptor4ai.

Provides a singleton manager to handle JSON-based translations with 
support for dot-notation keys and string interpolation.
"""

import json
import logging
import os
from typing import Any, Dict

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------
DEFAULT_LOCALE = "en"
LOCALES_DIR_NAME = "locales"


class I18n:
    """
    Internationalization Manager.

    Handles loading JSON translation files and retrieving strings
    based on dot-notation keys (e.g., 'gui.buttons.process').
    """

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self._locale = locale
        self._translations: Dict[str, Any] = {}
        self.is_loaded = False

        # Determine absolute path to 'locales' folder
        # src/transcriptor4ai/utils/i18n.py -> src/transcriptor4ai/locales
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._locales_path = os.path.join(base_dir, LOCALES_DIR_NAME)

        self.load_locale(locale)

    def load_locale(self, locale: str) -> None:
        """
        Load the translation file for the specified locale code.

        Falls back to an empty dictionary if the file is not found or invalid.
        """
        file_path = os.path.join(self._locales_path, f"{locale}.json")

        if not os.path.exists(file_path):
            logger.warning(f"Locale file not found: {file_path}. Falling back to raw keys.")
            self._translations = {}
            self.is_loaded = False
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
            self._locale = locale
            self.is_loaded = True
            logger.debug(f"Loaded locale: {locale}")
        except Exception as e:
            logger.error(f"Failed to parse locale file {file_path}: {e}")
            self._translations = {}
            self.is_loaded = False

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Translate a key string using dot-notation.

        Args:
            key: Dot-separated path to the string (e.g. 'gui.buttons.process').
            **kwargs: Variables to interpolate into the string (e.g. path=p).

        Returns:
            The translated string with placeholders filled.
            Returns the 'key' itself if the translation is missing or not a string.
        """
        keys = key.split(".")
        current_val: Any = self._translations

        try:
            # Traverse the dictionary using the keys
            for k in keys:
                if isinstance(current_val, dict):
                    current_val = current_val.get(k)
                else:
                    current_val = None
                    break

            # Validation: The final value must be a string
            if not isinstance(current_val, str):
                return key

            # Safe cast for Mypy: current_val is now guaranteed to be str
            translated_str: str = current_val

            if kwargs:
                return translated_str.format(**kwargs)

            return translated_str

        except Exception as e:
            logger.debug(f"Translation interpolation error for key '{key}': {e}")
            return key


# -----------------------------------------------------------------------------
# Global Singleton Instance
# -----------------------------------------------------------------------------
i18n = I18n(DEFAULT_LOCALE)