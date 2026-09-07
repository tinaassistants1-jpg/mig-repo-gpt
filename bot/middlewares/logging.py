"""Журналирование апдейтов: кто, что прислал, какой хендлер, с каким итогом."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

logger = logging.getLogger("leadbot.updates")


def _describe(event: TelegramObject) -> str:
    if isinstance(event, Message):
        if event.text:
            return f"message: {event.text[:80]}"
        if event.contact:
            return "message: <contact>"
        return f"message: <{event.content_type}>"
    if isinstance(event, CallbackQuery):
        return f"callback: {event.data}"
    return type(event).__name__


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        actor = f"{user.id} (@{user.username})" if user else "unknown"
        started = time.monotonic()
        try:
            result = await handler(event, data)
        except Exception as error:
            logger.exception(
                "кто=%s | что=%s | хендлер=%s | результат=ОШИБКА %s",
                actor,
                _describe(event),
                data.get("handler"),
                error,
            )
            raise
        elapsed_ms = (time.monotonic() - started) * 1000
        logger.info(
            "кто=%s | что=%s | хендлер=%s | результат=ok за %.0f мс",
            actor,
            _describe(event),
            getattr(data.get("handler"), "callback", None).__name__ if data.get("handler") else "-",
            elapsed_ms,
        )
        return result
