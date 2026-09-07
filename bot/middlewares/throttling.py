"""Простой антифлуд: не чаще одного апдейта в `rate` секунд на пользователя."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from bot import texts

_CLEANUP_EVERY = 500


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, rate: float = 0.5) -> None:
        self.rate = rate
        self._last_seen: dict[int, float] = {}
        self._calls_since_cleanup = 0

    def _cleanup(self, now: float) -> None:
        """Периодически чистим словарь, чтобы он не рос бесконечно."""
        self._calls_since_cleanup += 1
        if self._calls_since_cleanup < _CLEANUP_EVERY:
            return
        self._calls_since_cleanup = 0
        stale = [uid for uid, seen in self._last_seen.items() if now - seen > 60]
        for uid in stale:
            del self._last_seen[uid]

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or self.rate <= 0:
            return await handler(event, data)

        now = time.monotonic()
        self._cleanup(now)
        last = self._last_seen.get(user.id)
        if last is not None and now - last < self.rate:
            # Тихо гасим флуд: пользователю отвечаем один раз, обработчик не зовём.
            if isinstance(event, CallbackQuery):
                await event.answer(texts.ERR_THROTTLED, show_alert=False)
            elif isinstance(event, Message):
                await event.answer(texts.ERR_THROTTLED)
            return None

        self._last_seen[user.id] = now
        return await handler(event, data)
