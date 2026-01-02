from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, Optional

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
        self._loaded = False

        # Determine absolute path to 'locales' folder
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._locales_path = os.path.join(base_dir, LOCALES_DIR_NAME)

        self.load_locale(locale)

    def load_locale(self, locale: str) -> None:
        """
        Load the translation file for the specified locale code.
        Falls back to empty dict if file not found (logging warning).
        """
        file_path = os.path.join(self._locales_path, f"{locale}.json")

        if not os.path.exists(file_path):
            logger.warning(f"Locale file not found: {file_path}. Falling back to raw keys.")
            self._translations = {}
            self._loaded = False
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
            self._locale = locale
            self._loaded = True
            logger.debug(f"Loaded locale: {locale}")
        except Exception as e:
            logger.error(f"Failed to parse locale file {file_path}: {e}")
            self._translations = {}

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Translate a key string.

        Args:
            key: Dot-separated path to the string (e.g. 'gui.buttons.process').
            **kwargs: Variables to interpolate into the string (e.g. count=5).

        Returns:
            The translated string with placeholders filled.
            Returns the 'key' itself if translation is missing.
        """
        keys = key.split(".")
        value: Any = self._translations

        try:
            for k in keys:
                if isinstance(value, dict):
                    value = value.get(k)
                else:
                    value = None
                    break

            if value is None or not isinstance(value, str):
                return key

            # Interpolate variables if present
            if kwargs:
                return value.format(**kwargs)

            return value

        except Exception:
            return key


# -----------------------------------------------------------------------------
# Global Singleton Instance
# -----------------------------------------------------------------------------
i18n = I18n(DEFAULT_LOCALE)