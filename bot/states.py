"""Состояния FSM для сбора заявки."""

from aiogram.fsm.state import State, StatesGroup


class LeadForm(StatesGroup):
    service = State()
    budget = State()
    description = State()
    name = State()
    contact = State()
    confirm = State()
