"""Фильтры доступа."""

from __future__ import annotations

from aiogram.filters import Filter
from aiogram.types import Message

from bot.config import Settings


class IsAdmin(Filter):
    """Пропускает только пользователей из ADMIN_IDS."""

    async def __call__(self, message: Message, settings: Settings) -> bool:
        user = message.from_user
        return user is not None and settings.is_admin(user.id)
