"""Глобальный обработчик ошибок и запасной ответ на непонятные сообщения."""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, ExceptionTypeFilter
from aiogram.types import CallbackQuery, ErrorEvent, Message

from bot import keyboards, texts
from bot.config import Settings

logger = logging.getLogger("leadbot.errors")

ADMIN_COMMANDS = ("leads", "lead_info", "status", "stats", "export", "audit", "admin")


def build_router() -> Router:
    router = Router(name="errors")

    @router.errors(ExceptionTypeFilter(Exception))
    async def on_error(event: ErrorEvent) -> bool:
        """Пишет ошибку в лог и, если возможно, извиняется перед пользователем."""
        logger.exception("Необработанная ошибка: %s", event.exception)

        update = event.update
        target: Message | None = None
        if update.message is not None:
            target = update.message
        elif update.callback_query is not None and isinstance(
            update.callback_query.message, Message
        ):
            target = update.callback_query.message

        if target is not None:
            try:
                await target.answer(texts.ERR_UNKNOWN, reply_markup=keyboards.main_menu())
            except TelegramAPIError as send_error:
                logger.warning("Не удалось отправить сообщение об ошибке: %s", send_error)
        return True

    return router


def build_fallback_router() -> Router:
    """Запасные хендлеры. Подключаются последними — ловят всё, что не разобрали."""
    router = Router(name="fallback")

    @router.message(Command(*ADMIN_COMMANDS))
    async def not_admin(message: Message, settings: Settings) -> None:
        """Админ-роутер такое сообщение не взял — значит, прав нет."""
        await message.answer(texts.ERR_NOT_ADMIN)

    @router.message(F.text)
    async def unknown_message(message: Message) -> None:
        await message.answer(texts.HELP, reply_markup=keyboards.main_menu())

    @router.callback_query()
    async def stale_callback(callback: CallbackQuery) -> None:
        """Кнопка из старого сообщения после рестарта бота."""
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())

    return router
