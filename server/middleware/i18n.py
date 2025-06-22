"""Internationalization middleware for Zoho MCP Server."""

import logging
from typing import Any

from babel.support import Translations
from fastapi import Request

logger = logging.getLogger(__name__)


class I18nManager:
    """Internationalization manager for handling multiple languages."""

    def __init__(self) -> None:
        """Initialize i18n manager."""
        self.supported_locales = ["en", "ja"]
        self.default_locale = "en"
        self.translations: dict[str, Optional[Translations]] = {}

        # Initialize translations
        self._load_translations()

        logger.info(f"I18n manager initialized with locales: {self.supported_locales}")

    def _load_translations(self) -> None:
        """Load translation files."""
        for locale_code in self.supported_locales:
            try:
                # In a real implementation, load from .po/.mo files
                # For now, use dummy translations
                self.translations[locale_code] = None
                logger.debug(f"Loaded translations for {locale_code}")
            except Exception as e:
                logger.warning(f"Failed to load translations for {locale_code}: {e}")
                self.translations[locale_code] = None

    def get_locale_from_request(self, request: Request) -> str:
        """Extract locale from request.

        Args:
            request: FastAPI request

        Returns:
            Locale code
        """
        # Check query parameter first
        locale = request.query_params.get("locale")
        if locale and self._is_supported_locale(locale):
            return locale

        # Check Accept-Language header
        accept_language = request.headers.get("Accept-Language", "")
        if accept_language:
            # Parse Accept-Language header (simplified)
            for lang_range in accept_language.split(","):
                lang = lang_range.split(";")[0].strip().lower()
                # Extract language code (e.g., "en-US" -> "en")
                lang_code = lang.split("-")[0]
                if self._is_supported_locale(lang_code):
                    return lang_code

        return self.default_locale

    def _is_supported_locale(self, locale: str) -> bool:
        """Check if locale is supported.

        Args:
            locale: Locale code to check

        Returns:
            True if supported
        """
        return locale.lower() in self.supported_locales

    def translate(self, message: str, locale: Optional[str] = None) -> str:
        """Translate message to specified locale.

        Args:
            message: Message to translate
            locale: Target locale

        Returns:
            Translated message
        """
        if not locale:
            locale = self.default_locale

        # For now, return predefined translations
        translations = {
            "en": {
                "task_created": "Task created successfully",
                "task_updated": "Task updated successfully",
                "task_not_found": "Task not found",
                "file_uploaded": "File uploaded successfully",
                "file_not_found": "File not found",
                "invalid_parameters": "Invalid parameters",
                "internal_error": "Internal server error",
                "access_denied": "Access denied",
                "rate_limit_exceeded": "Rate limit exceeded"
            },
            "ja": {
                "task_created": "タスクが正常に作成されました",
                "task_updated": "タスクが正常に更新されました",
                "task_not_found": "タスクが見つかりません",
                "file_uploaded": "ファイルが正常にアップロードされました",
                "file_not_found": "ファイルが見つかりません",
                "invalid_parameters": "無効なパラメータです",
                "internal_error": "内部サーバーエラー",
                "access_denied": "アクセスが拒否されました",
                "rate_limit_exceeded": "レート制限を超過しました"
            }
        }

        locale_translations = translations.get(locale, translations[self.default_locale])
        return locale_translations.get(message, message)

    def format_response_message(
        self,
        message_key: str,
        locale: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """Format response message with parameters.

        Args:
            message_key: Message key to translate
            locale: Target locale
            **kwargs: Format parameters

        Returns:
            Formatted message
        """
        translated = self.translate(message_key, locale)

        try:
            return translated.format(**kwargs) if kwargs else translated
        except Exception as e:
            logger.warning(f"Failed to format message '{message_key}': {e}")
            return translated


# Global i18n manager instance
i18n_manager = I18nManager()
