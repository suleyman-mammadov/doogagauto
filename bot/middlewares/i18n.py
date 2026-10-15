import logging
from typing import Callable, Dict, Any, Awaitable, Optional
from aiogram import BaseMiddleware  # type: ignore
from aiogram.types import TelegramObject, User  # type: ignore

from database.queries import get_user_language

logger = logging.getLogger(__name__)

# Fast in-memory cache for user language codes
_USER_LANG_CACHE: Dict[int, str] = {}


def set_cached_user_language(user_id: int, lang: str):
    """Update user language in memory cache."""
    _USER_LANG_CACHE[user_id] = (lang or "en").lower()


def get_cached_user_language(user_id: int) -> Optional[str]:
    """Get user language from memory cache."""
    return _USER_LANG_CACHE.get(user_id)


class I18nMiddleware(BaseMiddleware):
    """Aiogram middleware that resolves user language and injects data['lang']."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user: Optional[User] = data.get("event_from_user")
        
        lang = "en"
        if user:
            user_id = user.id
            cached_lang = _USER_LANG_CACHE.get(user_id)
            if cached_lang:
                lang = cached_lang
            else:
                try:
                    db_lang = await get_user_language(user_id)
                    if db_lang:
                        lang = db_lang
                        _USER_LANG_CACHE[user_id] = lang
                    else:
                        lang = "en"
                except Exception as e:
                    logger.debug(f"Failed to fetch user language from DB: {e}")
                    lang = "en"

        data["lang"] = lang
        return await handler(event, data)
