"""Точка входа: сборка приложения и запуск long polling."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import Settings, get_settings
from bot.db.base import create_engine, create_session_factory
from bot.handlers import build_router
from bot.logging_setup import setup_logging
from bot.middlewares import DatabaseMiddleware, LoggingMiddleware, ThrottlingMiddleware

logger = logging.getLogger("leadbot")

USER_COMMANDS = [
    BotCommand(command="start", description="Главное меню"),
    BotCommand(command="lead", description="Оставить заявку"),
    BotCommand(command="cancel", description="Отменить заполнение"),
    BotCommand(command="help", description="Справка"),
]


def build_storage(settings: Settings) -> BaseStorage:
    """Redis, если он задан; иначе память (состояния живут до рестарта)."""
    if not settings.redis_url:
        logger.warning("REDIS_URL не задан — использую MemoryStorage")
        return MemoryStorage()

    from aiogram.fsm.storage.redis import RedisStorage

    return RedisStorage.from_url(settings.redis_url)


def build_dispatcher(settings: Settings, storage: BaseStorage, session_factory) -> Dispatcher:
    dispatcher = Dispatcher(storage=storage)
    dispatcher["settings"] = settings

    # Внешние мидлвари видят все апдейты, включая отфильтрованные.
    dispatcher.update.outer_middleware(LoggingMiddleware())
    dispatcher.update.outer_middleware(DatabaseMiddleware(session_factory))
    dispatcher.update.outer_middleware(ThrottlingMiddleware(settings.throttle_rate))

    dispatcher.include_router(build_router())
    return dispatcher


async def main() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    if not settings.admin_ids:
        logger.warning("ADMIN_IDS пуст — уведомления о заявках отправлять некому")

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    storage = build_storage(settings)
    dispatcher = build_dispatcher(settings, storage, session_factory)

    try:
        await bot.set_my_commands(USER_COMMANDS)
        me = await bot.get_me()
        logger.info("Бот @%s запущен", me.username)
        await dispatcher.start_polling(bot, allowed_updates=dispatcher.resolve_used_update_types())
    finally:
        logger.info("Остановка: закрываю соединения")
        await storage.close()
        await bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Остановлено пользователем")
