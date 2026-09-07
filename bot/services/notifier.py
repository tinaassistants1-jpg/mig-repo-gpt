"""Доставка уведомлений о новых заявках администраторам."""

from __future__ import annotations

import logging

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

logger = logging.getLogger("leadbot.notifier")


async def notify_admins(bot: Bot, chat_ids: list[int], text: str) -> int:
    """Разослать текст по чатам. Возвращает число успешных отправок.

    Ошибка доставки в один чат не должна ронять обработку заявки — клиент уже
    получил подтверждение, поэтому исключения гасим и пишем в лог.
    """
    delivered = 0
    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id, text)
        except TelegramAPIError as error:
            logger.warning("Не удалось отправить уведомление в чат %s: %s", chat_id, error)
        else:
            delivered += 1
    if not delivered and chat_ids:
        logger.error("Уведомление о заявке не доставлено ни в один из чатов: %s", chat_ids)
    return delivered
