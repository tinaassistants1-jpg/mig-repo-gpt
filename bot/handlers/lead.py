"""Сбор заявки: пошаговый диалог на FSM."""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import keyboards, texts
from bot.catalog import budget_title, is_budget, is_service, service_title
from bot.config import Settings
from bot.db.repo import LeadDraft, Repository
from bot.keyboards import BudgetCB, ConfirmCB, ServiceCB
from bot.services.notifier import notify_admins
from bot.states import LeadForm
from bot.utils import validators

REQUIRED_FIELDS = ("service", "budget", "description", "contact_name", "contact_value")


def draft_card(data: dict, lead_id: int | None = None, author: str | None = None) -> str:
    """Отрисовать карточку из данных, накопленных в FSM."""
    return texts.lead_card(
        lead_id=lead_id,
        service=service_title(data.get("service", "")),
        budget=budget_title(data.get("budget", "")),
        description=data.get("description", ""),
        contact_name=data.get("contact_name", ""),
        contact_value=data.get("contact_value", ""),
        author=author,
    )


async def _start_form(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(LeadForm.service)
    await message.answer(texts.ASK_SERVICE, reply_markup=keyboards.services_keyboard())


async def _show_confirmation(message: Message, state: FSMContext, contact: str) -> None:
    await state.update_data(contact_value=contact)
    await state.set_state(LeadForm.confirm)
    data = await state.get_data()
    await message.answer(texts.CONFIRM_INTRO, reply_markup=keyboards.remove_keyboard())
    await message.answer(draft_card(data), reply_markup=keyboards.confirm_keyboard())


def build_router() -> Router:
    router = Router(name="lead")

    # ── Вход в диалог ─────────────────────────────────────────────────────

    @router.message(Command("lead"))
    @router.message(F.text == keyboards.BTN_NEW_LEAD)
    async def start_lead(message: Message, state: FSMContext) -> None:
        await _start_form(message, state)

    @router.message(Command("cancel"))
    async def cancel(message: Message, state: FSMContext) -> None:
        """Прервать заполнение на любом шаге."""
        if await state.get_state() is None:
            await message.answer(texts.NOTHING_TO_CANCEL, reply_markup=keyboards.main_menu())
            return
        await state.clear()
        await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())

    # ── Шаг 1: услуга ─────────────────────────────────────────────────────
    # Фильтра по состоянию нет намеренно: тот же список услуг показывается из
    # главного меню, и клик по нему должен начинать заявку.

    @router.callback_query(ServiceCB.filter())
    async def pick_service(
        callback: CallbackQuery, callback_data: ServiceCB, state: FSMContext
    ) -> None:
        if not is_service(callback_data.code):
            await callback.answer(texts.ERR_UNKNOWN, show_alert=True)
            return

        await state.update_data(service=callback_data.code)
        await state.set_state(LeadForm.budget)
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(
                texts.ASK_BUDGET, reply_markup=keyboards.budgets_keyboard()
            )

    # ── Шаг 2: бюджет ─────────────────────────────────────────────────────

    @router.callback_query(BudgetCB.filter(), StateFilter(LeadForm.budget))
    async def pick_budget(
        callback: CallbackQuery, callback_data: BudgetCB, state: FSMContext
    ) -> None:
        if not is_budget(callback_data.code):
            await callback.answer(texts.ERR_UNKNOWN, show_alert=True)
            return

        await state.update_data(budget=callback_data.code)
        await state.set_state(LeadForm.description)
        await callback.answer()
        if callback.message is not None:
            await callback.message.answer(texts.ASK_DESCRIPTION)

    # ── Шаг 3: описание задачи ────────────────────────────────────────────

    @router.message(StateFilter(LeadForm.description), F.text)
    async def set_description(message: Message, state: FSMContext) -> None:
        description, error = validators.validate_description(message.text or "")
        if error == "short":
            await message.answer(
                texts.ERR_DESCRIPTION_SHORT.format(min_len=validators.DESCRIPTION_MIN)
            )
            return
        if error == "long":
            await message.answer(
                texts.ERR_DESCRIPTION_LONG.format(max_len=validators.DESCRIPTION_MAX)
            )
            return

        await state.update_data(description=description)
        await state.set_state(LeadForm.name)
        await message.answer(texts.ASK_NAME)

    @router.message(StateFilter(LeadForm.description))
    async def description_not_text(message: Message) -> None:
        await message.answer(texts.ERR_EXPECTED_TEXT)

    # ── Шаг 4: имя ────────────────────────────────────────────────────────

    @router.message(StateFilter(LeadForm.name), F.text)
    async def set_name(message: Message, state: FSMContext) -> None:
        name = validators.validate_name(message.text or "")
        if name is None:
            await message.answer(
                texts.ERR_NAME_INVALID.format(
                    min_len=validators.NAME_MIN, max_len=validators.NAME_MAX
                )
            )
            return

        await state.update_data(contact_name=name)
        await state.set_state(LeadForm.contact)
        await message.answer(texts.ASK_CONTACT, reply_markup=keyboards.contact_keyboard())

    @router.message(StateFilter(LeadForm.name))
    async def name_not_text(message: Message) -> None:
        await message.answer(texts.ERR_EXPECTED_TEXT)

    # ── Шаг 5: контакт ────────────────────────────────────────────────────

    @router.message(StateFilter(LeadForm.contact), F.contact)
    async def set_contact_shared(message: Message, state: FSMContext) -> None:
        """Номер, присланный кнопкой «Поделиться номером»."""
        contact = message.contact
        if contact is None:
            await message.answer(texts.ERR_CONTACT_INVALID)
            return
        await _show_confirmation(message, state, validators.normalize_phone(contact.phone_number))

    @router.message(StateFilter(LeadForm.contact), F.text)
    async def set_contact_typed(message: Message, state: FSMContext) -> None:
        contact = validators.validate_contact(message.text or "")
        if contact is None:
            await message.answer(texts.ERR_CONTACT_INVALID)
            return
        await _show_confirmation(message, state, contact)

    @router.message(StateFilter(LeadForm.contact))
    async def contact_not_supported(message: Message) -> None:
        await message.answer(texts.ERR_CONTACT_INVALID)

    # ── Шаг 6: подтверждение и сохранение ─────────────────────────────────

    @router.callback_query(ConfirmCB.filter(), StateFilter(LeadForm.confirm))
    async def confirm(
        callback: CallbackQuery,
        callback_data: ConfirmCB,
        state: FSMContext,
        repo: Repository,
        bot: Bot,
        settings: Settings,
    ) -> None:
        message = callback.message
        user = callback.from_user

        if callback_data.action == "cancel":
            await state.clear()
            await callback.answer()
            if message is not None:
                await message.answer(texts.CANCELLED, reply_markup=keyboards.main_menu())
            return

        if callback_data.action == "restart":
            await callback.answer()
            if message is not None:
                await _start_form(message, state)
            return

        if callback_data.action != "send":
            await callback.answer(texts.ERR_UNKNOWN, show_alert=True)
            return

        data = await state.get_data()
        if not all(data.get(field) for field in REQUIRED_FIELDS):
            # Состояние потерялось (рестарт бота, устаревшая кнопка) — начинаем заново.
            await state.clear()
            await callback.answer()
            if message is not None:
                await message.answer(texts.ERR_UNKNOWN, reply_markup=keyboards.main_menu())
            return

        db_user = await repo.upsert_user(user.id, user.username, user.full_name)
        lead = await repo.create_lead(
            db_user,
            LeadDraft(
                service=data["service"],
                budget=data["budget"],
                description=data["description"],
                contact_name=data["contact_name"],
                contact_value=data["contact_value"],
            ),
        )
        await repo.log_action(
            user.id,
            "client",
            "lead_created",
            f"заявка сохранена: {lead.service}",
            f"lead:{lead.id}",
        )
        await state.clear()
        await callback.answer()

        if message is not None:
            await message.answer(
                texts.LEAD_SAVED.format(lead_id=lead.id), reply_markup=keyboards.main_menu()
            )

        author = f"@{user.username}" if user.username else f"id{user.id}"
        card = draft_card(data, lead_id=lead.id, author=author)
        await notify_admins(bot, settings.notify_targets, texts.new_lead_notification(card))

    return router
