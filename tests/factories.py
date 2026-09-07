"""Фабрики Telegram-апдейтов для тестов."""

from __future__ import annotations

import itertools
from datetime import datetime

from aiogram.types import CallbackQuery, Chat, Contact, Message, Update
from aiogram.types import User as TgUser

_ids = itertools.count(1000)


def user(user_id: int, username: str | None = "client") -> TgUser:
    return TgUser(id=user_id, is_bot=False, first_name="Тест", username=username)


def message(text: str, user_id: int, username: str | None = "client") -> Message:
    return Message(
        message_id=next(_ids),
        date=datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=user(user_id, username),
        text=text,
    )


def contact_message(phone: str, user_id: int) -> Message:
    return Message(
        message_id=next(_ids),
        date=datetime.now(),
        chat=Chat(id=user_id, type="private"),
        from_user=user(user_id),
        contact=Contact(phone_number=phone, first_name="Тест", user_id=user_id),
    )


def message_update(text: str, user_id: int, username: str | None = "client") -> Update:
    return Update(update_id=next(_ids), message=message(text, user_id, username))


def contact_update(phone: str, user_id: int) -> Update:
    return Update(update_id=next(_ids), message=contact_message(phone, user_id))


def callback_update(data: str, user_id: int) -> Update:
    return Update(
        update_id=next(_ids),
        callback_query=CallbackQuery(
            id=str(next(_ids)),
            from_user=user(user_id),
            chat_instance="test",
            data=data,
            message=message("предыдущее сообщение", user_id),
        ),
    )
