"""Клавиатуры бота и фабрики callback-данных."""

from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.catalog import BUDGETS, SERVICES

BTN_NEW_LEAD = "📝 Оставить заявку"
BTN_SERVICES = "🧩 Услуги"
BTN_ABOUT = "ℹ️ О нас"
BTN_SHARE_PHONE = "📱 Поделиться номером"


class ServiceCB(CallbackData, prefix="svc"):
    code: str


class BudgetCB(CallbackData, prefix="bdg"):
    code: str


class ConfirmCB(CallbackData, prefix="cfm"):
    action: str  # send | restart | cancel


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=BTN_NEW_LEAD)],
            [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_ABOUT)],
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите пункт меню",
    )


def services_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in SERVICES:
        builder.button(text=option.title, callback_data=ServiceCB(code=option.code))
    builder.adjust(1)
    return builder.as_markup()


def budgets_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for option in BUDGETS:
        builder.button(text=option.title, callback_data=BudgetCB(code=option.code))
    builder.adjust(1)
    return builder.as_markup()


def contact_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_SHARE_PHONE, request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Телефон, e-mail или @username",
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Отправить", callback_data=ConfirmCB(action="send").pack()
                )
            ],
            [
                InlineKeyboardButton(
                    text="✏️ Заполнить заново", callback_data=ConfirmCB(action="restart").pack()
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отменить", callback_data=ConfirmCB(action="cancel").pack()
                )
            ],
        ]
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()
