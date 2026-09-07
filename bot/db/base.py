"""Подключение к базе: движок и фабрика сессий."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from bot.db.models import Base


def create_engine(database_url: str, echo: bool = False) -> AsyncEngine:
    return create_async_engine(database_url, echo=echo, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def create_all(engine: AsyncEngine) -> None:
    """Создать схему напрямую, без миграций.

    Используется в тестах и при локальном запуске на SQLite. В проде схему
    раскатывает Alembic (`alembic upgrade head`).
    """
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
