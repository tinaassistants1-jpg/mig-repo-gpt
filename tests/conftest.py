"""Общие фикстуры: подменённый Telegram-сессия, БД в памяти, диспетчер."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import pytest
import pytest_asyncio
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.base import BaseSession
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.methods import TelegramMethod
from aiogram.types import Chat
from aiogram.types import Message as TgMessage
from aiogram.types import User as TgUser
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from bot.__main__ import build_dispatcher
from bot.config import Settings
from bot.db.base import create_all, create_engine, create_session_factory
from bot.db.repo import Repository

ADMIN_ID = 100_000_001
CLIENT_ID = 200_000_002

BOT_USER = TgUser(id=42, is_bot=True, first_name="LeadBot", username="leadbot")
BOT_CHAT = Chat(id=42, type="private")


class RecordingSession(BaseSession):
    """Вместо походов в Telegram складывает вызовы в список."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[TelegramMethod[Any]] = []

    async def close(self) -> None:  # pragma: no cover - ничего не держим
        pass

    async def stream_content(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise NotImplementedError

    # Сигнатуру задаёт aiogram BaseSession, поэтому timeout здесь обязателен.
    async def make_request(
        self,
        bot: Bot,
        method: TelegramMethod[Any],
        timeout: int | None = None,  # noqa: ASYNC109
    ) -> Any:
        self.requests.append(method)
        name = type(method).__name__
        if name in {"SendMessage", "SendDocument", "AnswerDocument"}:
            return TgMessage(
                message_id=len(self.requests),
                date=datetime.now(),
                chat=Chat(id=getattr(method, "chat_id", 0), type="private"),
                from_user=BOT_USER,
                text=getattr(method, "text", None),
            )
        if name == "GetMe":
            return BOT_USER
        return True

    # ── помощники для тестов ──────────────────────────────────────────────

    def texts(self) -> list[str]:
        return [m.text for m in self.requests if type(m).__name__ == "SendMessage"]

    def last_text(self) -> str:
        texts = self.texts()
        assert texts, "бот не отправил ни одного сообщения"
        return texts[-1]

    def methods(self) -> list[str]:
        return [type(m).__name__ for m in self.requests]

    def clear(self) -> None:
        self.requests.clear()


@pytest.fixture
def settings() -> Settings:
    return Settings(
        bot_token="42:TEST-TOKEN",
        admin_ids=[ADMIN_ID],
        notify_chat_id=None,
        database_url="sqlite+aiosqlite:///:memory:",
        redis_url=None,
        throttle_rate=0.0,  # антифлуд мешает быстрым тестам
    )


@pytest.fixture
def session() -> RecordingSession:
    return RecordingSession()


@pytest.fixture
def bot(session: RecordingSession, settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        session=session,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


@pytest_asyncio.fixture
async def session_factory() -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Одна SQLite-база в памяти на тест, схема создаётся из моделей."""
    engine = create_engine("sqlite+aiosqlite:///:memory:")
    await create_all(engine)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest_asyncio.fixture
async def repo(
    session_factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[Repository]:
    async with session_factory() as db_session:
        yield Repository(db_session)
        await db_session.commit()


@pytest.fixture
def dispatcher(settings: Settings, session_factory: async_sessionmaker[AsyncSession]) -> Dispatcher:
    return build_dispatcher(settings, MemoryStorage(), session_factory)
