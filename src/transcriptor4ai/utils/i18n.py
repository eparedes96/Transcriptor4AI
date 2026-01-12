from __future__ import annotations

"""
Internationalization (i18n) Utility.

Singleton manager for loading and accessing translation strings.
Supports dot-notation keys (e.g., 'gui.menu.file') and argument interpolation.
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
LOCALES_REL_PATH = os.path.join("..", "interface", "locales")


class I18n:
    """
    Internationalization Manager.

    Loads JSON files from the 'interface/locales' directory and provides
    safe access to translation strings.
    """

    def __init__(self, locale: str = DEFAULT_LOCALE):
        self._locale = locale
        self._translations: Dict[str, Any] = {}
        self.is_loaded = False

        # Calculate absolute path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self._locales_path = os.path.abspath(os.path.join(base_dir, LOCALES_REL_PATH))

        self.load_locale(locale)

    def load_locale(self, locale: str) -> None:
        """
        Load a translation file by locale code.

        Args:
            locale: The locale code (e.g., 'en', 'es').
        """
        file_path = os.path.join(self._locales_path, f"{locale}.json")

        if not os.path.exists(file_path):
            logger.warning(f"Locale file not found: {file_path}. Using fallback keys.")
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
        Retrieve and format a translation string.

        Args:
            key: Dot-separated key path (e.g. 'gui.title').
            **kwargs: Replacement variables for the string format.

        Returns:
            str: The translated and formatted string, or the key itself if missing.
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

            return current_val.format(**kwargs) if kwargs else current_val

        except Exception as e:
            logger.debug(f"Translation error for '{key}': {e}")
            return key


# -----------------------------------------------------------------------------
# Global Singleton
# -----------------------------------------------------------------------------
i18n = I18n(DEFAULT_LOCALE)