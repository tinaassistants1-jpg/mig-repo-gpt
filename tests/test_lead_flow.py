"""Сквозной сценарий: клиент проходит диалог и заявка попадает в базу."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import keyboards, texts
from bot.db.models import LeadStatus
from bot.db.repo import Repository
from tests import factories as f
from tests.conftest import ADMIN_ID, CLIENT_ID, RecordingSession

DESCRIPTION = "Нужен лендинг для студии с формой заявки и оплатой"


async def _walk_to_confirm(dispatcher: Dispatcher, bot: Bot) -> None:
    """Пройти диалог до экрана подтверждения."""
    await dispatcher.feed_update(bot, f.message_update("/start", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(keyboards.BTN_NEW_LEAD, CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("svc:website", CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("bdg:50_150", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(DESCRIPTION, CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update("Тина", CLIENT_ID))
    await dispatcher.feed_update(bot, f.contact_update("+7 999 123-45-67", CLIENT_ID))


async def test_happy_path_creates_lead(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _walk_to_confirm(dispatcher, bot)

    confirm_card = session.last_text()
    assert "Сайт / лендинг" in confirm_card
    assert "50 000 — 150 000 ₽" in confirm_card
    assert "+79991234567" in confirm_card

    session.clear()
    await dispatcher.feed_update(bot, f.callback_update("cfm:send", CLIENT_ID))

    async with session_factory() as db_session:
        leads = await Repository(db_session).list_leads()

    assert len(leads) == 1
    lead = leads[0]
    assert lead.service == "website"
    assert lead.budget == "50_150"
    assert lead.description == DESCRIPTION
    assert lead.contact_name == "Тина"
    assert lead.contact_value == "+79991234567"
    assert lead.status is LeadStatus.new
    assert lead.user.telegram_id == CLIENT_ID

    # Клиент получил подтверждение...
    replies = session.texts()
    assert any(f"Заявка №{lead.id} принята" in text for text in replies)

    # ...а админ — уведомление в свой чат.
    notifications = [
        method
        for method in session.requests
        if type(method).__name__ == "SendMessage" and method.chat_id == ADMIN_ID
    ]
    assert len(notifications) == 1
    assert "Новая заявка" in notifications[0].text
    assert DESCRIPTION in notifications[0].text


async def test_short_description_is_rejected(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/start", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(keyboards.BTN_NEW_LEAD, CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("svc:bot", CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("bdg:lt_50", CLIENT_ID))

    session.clear()
    await dispatcher.feed_update(bot, f.message_update("бот", CLIENT_ID))
    assert "Слишком коротко" in session.last_text()

    # Шаг не пройден: следующий ответ по-прежнему ждут как описание.
    session.clear()
    await dispatcher.feed_update(bot, f.message_update("Нужен бот приёма заявок", CLIENT_ID))
    assert session.last_text() == texts.ASK_NAME


async def test_invalid_contact_is_rejected(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/start", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(keyboards.BTN_NEW_LEAD, CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("svc:design", CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("bdg:unknown", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(DESCRIPTION, CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update("Тина", CLIENT_ID))

    session.clear()
    await dispatcher.feed_update(bot, f.message_update("позвоните мне", CLIENT_ID))
    assert "Не похоже на контакт" in session.last_text()


async def test_cancel_stops_the_form(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _walk_to_confirm(dispatcher, bot)

    session.clear()
    await dispatcher.feed_update(bot, f.callback_update("cfm:cancel", CLIENT_ID))
    assert texts.CANCELLED in session.texts()

    async with session_factory() as db_session:
        assert await Repository(db_session).list_leads() == []


async def test_cancel_command_without_form(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/cancel", CLIENT_ID))
    assert texts.NOTHING_TO_CANCEL in session.texts()


async def test_description_must_be_text(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/start", CLIENT_ID))
    await dispatcher.feed_update(bot, f.message_update(keyboards.BTN_NEW_LEAD, CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("svc:other", CLIENT_ID))
    await dispatcher.feed_update(bot, f.callback_update("bdg:unknown", CLIENT_ID))

    session.clear()
    await dispatcher.feed_update(bot, f.contact_update("+79991234567", CLIENT_ID))
    assert session.last_text() == texts.ERR_EXPECTED_TEXT


async def test_start_records_user_and_audit(
    dispatcher: Dispatcher, bot: Bot, session_factory: async_sessionmaker[AsyncSession]
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/start", CLIENT_ID))

    async with session_factory() as db_session:
        records = await Repository(db_session).recent_audit()

    assert [record.action for record in records] == ["start"]
    assert records[0].actor_id == CLIENT_ID
