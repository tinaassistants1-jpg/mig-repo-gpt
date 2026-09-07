"""Админские команды и разграничение доступа."""

from __future__ import annotations

from aiogram import Bot, Dispatcher
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot import texts
from bot.db.models import LeadStatus
from bot.db.repo import LeadDraft, Repository
from tests import factories as f
from tests.conftest import ADMIN_ID, CLIENT_ID, RecordingSession

DRAFT = LeadDraft(
    service="website",
    budget="150_500",
    description="Корпоративный сайт с блогом",
    contact_name="Тина",
    contact_value="+79991234567",
)


async def _seed_lead(session_factory: async_sessionmaker[AsyncSession]) -> int:
    async with session_factory() as db_session:
        repo = Repository(db_session)
        user = await repo.upsert_user(CLIENT_ID, "client", "Клиент")
        lead = await repo.create_lead(user, DRAFT)
        await db_session.commit()
        return lead.id


async def test_client_cannot_use_admin_commands(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/stats", CLIENT_ID))
    assert session.last_text() == texts.ERR_NOT_ADMIN


async def test_admin_sees_leads(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lead_id = await _seed_lead(session_factory)

    await dispatcher.feed_update(bot, f.message_update("/leads", ADMIN_ID, "manager"))
    card = session.last_text()
    assert f"Заявка №{lead_id}" in card
    assert "Корпоративный сайт с блогом" in card
    assert "🆕 Новая" in card


async def test_admin_changes_status(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lead_id = await _seed_lead(session_factory)

    await dispatcher.feed_update(
        bot, f.message_update(f"/status {lead_id} in_work", ADMIN_ID, "manager")
    )
    assert "В работе" in session.last_text()

    async with session_factory() as db_session:
        repo = Repository(db_session)
        lead = await repo.get_lead(lead_id)
        assert lead is not None and lead.status is LeadStatus.in_work

        actions = [record.action for record in await repo.recent_audit()]
        assert "lead_status_changed" in actions


async def test_status_rejects_unknown_value(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lead_id = await _seed_lead(session_factory)
    await dispatcher.feed_update(
        bot, f.message_update(f"/status {lead_id} maybe", ADMIN_ID, "manager")
    )
    assert "Неизвестный статус" in session.last_text()


async def test_status_reports_missing_lead(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/status 999 done", ADMIN_ID, "manager"))
    assert "не найдена" in session.last_text()


async def test_status_reports_bad_usage(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/status", ADMIN_ID, "manager"))
    assert "/status 12 in_work" in session.last_text()


async def test_stats(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_lead(session_factory)
    await dispatcher.feed_update(bot, f.message_update("/stats", ADMIN_ID, "manager"))

    text = session.last_text()
    assert "Всего заявок: 1" in text
    assert "Пользователей: 1" in text


async def test_export_sends_csv(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    await _seed_lead(session_factory)
    await dispatcher.feed_update(bot, f.message_update("/export", ADMIN_ID, "manager"))

    documents = [m for m in session.requests if type(m).__name__ == "SendDocument"]
    assert len(documents) == 1
    payload = documents[0].document.data.decode("utf-8-sig")
    assert "Корпоративный сайт с блогом" in payload
    assert documents[0].document.filename.endswith(".csv")


async def test_export_without_leads(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("/export", ADMIN_ID, "manager"))
    assert session.last_text() == texts.NO_LEADS


async def test_lead_info(
    dispatcher: Dispatcher,
    bot: Bot,
    session: RecordingSession,
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    lead_id = await _seed_lead(session_factory)
    await dispatcher.feed_update(
        bot, f.message_update(f"/lead_info {lead_id}", ADMIN_ID, "manager")
    )
    assert f"Заявка №{lead_id}" in session.last_text()


async def test_unknown_text_gets_help(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    await dispatcher.feed_update(bot, f.message_update("привет", CLIENT_ID))
    assert "Команды" in session.last_text()


async def test_stale_callback_is_answered(
    dispatcher: Dispatcher, bot: Bot, session: RecordingSession
) -> None:
    # Кнопка подтверждения без активного состояния — например, после рестарта бота.
    await dispatcher.feed_update(bot, f.callback_update("cfm:send", CLIENT_ID))
    assert texts.CANCELLED in session.texts()
