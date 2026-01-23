import json
import logging
import os
import sys  # <--- NEW IMPORT
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ==============================================================================
# SYSTEM DEFAULTS
# ==============================================================================
DEFAULT_LOCALE = "en"
# LOCALES_REL_PATH se elimina como constante global rígida

# ==============================================================================
# I18N MANAGER SERVICE
# ==============================================================================
class I18n:
    """
    Resource manager for locale-specific string translations.
    """

    def __init__(self, locale: str = DEFAULT_LOCALE) -> None:
        self._locale = locale
        self._translations: Dict[str, Any] = {}
        self.is_loaded = False

        # 1. RESOLVE RESOURCE PATH (Frozen vs Dev)
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a temporary folder at _MEIPASS
            base_dir = getattr(sys, '_MEIPASS', os.getcwd())
            # In bundled app, assets are usually mapped to root or specific folder
            self._locales_path = os.path.join(base_dir, "transcriptor4ai", "interface", "locales")
        else:
            # Standard development environment
            base_dir = os.path.dirname(os.path.abspath(__file__))
            self._locales_path = os.path.abspath(os.path.join(base_dir, "..", "interface", "locales"))

        self.load_locale(locale)

    def load_locale(self, locale: str) -> None:
        """
        Load a specific translation dictionary from the filesystem.

        Args:
            locale: ISO identifier for the target language.
        """
        file_path = os.path.join(self._locales_path, f"{locale}.json")

        if not os.path.exists(file_path):
            logger.warning(f"I18n: Locale resource missing at '{file_path}'. Fallback active.")
            self._translations = {}
            self.is_loaded = False
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)
            self._locale = locale
            self.is_loaded = True
            logger.debug(f"I18n: Successfully loaded locale dictionary: {locale}")
        except Exception as e:
            logger.error(f"I18n: Corruption in locale file {file_path}: {e}")
            self._translations = {}
            self.is_loaded = False

    def t(self, key: str, **kwargs: Any) -> str:
        """
        Resolve and format a translation string using dot-notation.

        Recursively traverses the active locale dictionary to find the
        requested key. If variables are provided, applies Python string
        interpolation.

        Args:
            key: Hierarchical identifier path (e.g., 'gui.buttons.save').
            **kwargs: Dynamic variables for string formatting.

        Returns:
            str: The translated and formatted string. Returns the key itself
                 as a fallback if resolution fails.
        """
        keys = key.split(".")
        current_val: Any = self._translations

        try:
            # 1. RESOLVE: Recursive resolution of nested dictionary keys
            for k in keys:
                if isinstance(current_val, dict):
                    current_val = current_val.get(k)
                else:
                    current_val = None
                    break

            # 2. VALIDATE: Terminal result must be a formatable string
            if not isinstance(current_val, str):
                return key

            # 3. INTERPOLATE: Apply dynamic variables if provided
            return current_val.format(**kwargs) if kwargs else current_val

        except Exception as e:
            logger.debug(f"I18n: Resolution error for path '{key}': {e}")
            return key

# ==============================================================================
# SERVICE INITIALIZATION
# ==============================================================================
# Global singleton instance for application-wide resource access
i18n = I18n(DEFAULT_LOCALE)