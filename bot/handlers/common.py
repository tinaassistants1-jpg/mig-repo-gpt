"""Общие команды: старт, справка, информационные разделы."""

from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot import keyboards, texts
from bot.db.repo import Repository


def build_router() -> Router:
    """Роутер собирается фабрикой: aiogram запрещает подключать один и тот же
    экземпляр Router дважды, а фабрика даёт свежий на каждый диспетчер."""
    router = Router(name="common")

    @router.message(CommandStart())
    async def cmd_start(message: Message, state: FSMContext, repo: Repository) -> None:
        """Сбрасывает незаконченный диалог и показывает главное меню."""
        await state.clear()
        user = message.from_user
        if user is not None:
            await repo.upsert_user(user.id, user.username, user.full_name)
            await repo.log_action(user.id, "client", "start", "показано главное меню")
        await message.answer(texts.START, reply_markup=keyboards.main_menu())

    @router.message(Command("help"))
    async def cmd_help(message: Message) -> None:
        await message.answer(texts.HELP, reply_markup=keyboards.main_menu())

    @router.message(F.text == keyboards.BTN_ABOUT)
    async def show_about(message: Message) -> None:
        await message.answer(texts.ABOUT, reply_markup=keyboards.main_menu())

    @router.message(F.text == keyboards.BTN_SERVICES)
    async def show_services(message: Message) -> None:
        """Список услуг — клик по услуге сразу начинает заполнение заявки."""
        await message.answer(texts.SERVICES_INTRO, reply_markup=keyboards.services_keyboard())

    return router
