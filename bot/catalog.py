"""Справочники услуг и бюджетов.

Вынесены отдельно, чтобы клавиатуры, тексты и валидация опирались на один
источник правды. Правится без изменения логики бота.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Option:
    code: str
    title: str


SERVICES: tuple[Option, ...] = (
    Option("website", "Сайт / лендинг"),
    Option("webapp", "Веб-приложение"),
    Option("bot", "Телеграм-бот"),
    Option("design", "Дизайн и UI/UX"),
    Option("automation", "Автоматизация и интеграции"),
    Option("other", "Другое"),
)

BUDGETS: tuple[Option, ...] = (
    Option("lt_50", "до 50 000 ₽"),
    Option("50_150", "50 000 — 150 000 ₽"),
    Option("150_500", "150 000 — 500 000 ₽"),
    Option("gt_500", "более 500 000 ₽"),
    Option("unknown", "Пока не определён"),
)

_SERVICE_BY_CODE = {option.code: option for option in SERVICES}
_BUDGET_BY_CODE = {option.code: option for option in BUDGETS}


def service_title(code: str) -> str:
    """Человекочитаемое название услуги; неизвестный код возвращается как есть."""
    option = _SERVICE_BY_CODE.get(code)
    return option.title if option else code


def budget_title(code: str) -> str:
    option = _BUDGET_BY_CODE.get(code)
    return option.title if option else code


def is_service(code: str) -> bool:
    return code in _SERVICE_BY_CODE


def is_budget(code: str) -> bool:
    return code in _BUDGET_BY_CODE
