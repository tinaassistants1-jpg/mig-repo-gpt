"""Проверка и нормализация пользовательского ввода.

Функции чистые и без зависимостей от aiogram — их удобно тестировать.
"""

from __future__ import annotations

import re

DESCRIPTION_MIN = 10
DESCRIPTION_MAX = 2000
NAME_MIN = 2
NAME_MAX = 64
CONTACT_MAX = 128

_PHONE_RE = re.compile(r"^\+?\d[\d\s\-()]{7,20}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s.]+\.[a-zA-Z]{2,}$")
_USERNAME_RE = re.compile(r"^@[A-Za-z0-9_]{4,32}$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def clean_text(value: str) -> str:
    """Убрать управляющие символы и схлопнуть лишние пробелы по краям."""
    return _CONTROL_RE.sub("", value).strip()


def validate_description(value: str) -> tuple[str | None, str | None]:
    """Вернуть (значение, ошибка). Ошибка — ключ шаблона из texts."""
    text = clean_text(value)
    if len(text) < DESCRIPTION_MIN:
        return None, "short"
    if len(text) > DESCRIPTION_MAX:
        return None, "long"
    return text, None


def validate_name(value: str) -> str | None:
    """Нормализованное имя или None, если оно не проходит проверку."""
    name = clean_text(value)
    if not NAME_MIN <= len(name) <= NAME_MAX:
        return None
    return name


def normalize_phone(value: str) -> str:
    """Привести телефон к виду +7XXXXXXXXXX (насколько это возможно)."""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return "+" + digits if digits else value


def validate_contact(value: str) -> str | None:
    """Телефон, e-mail или @username. None — формат не распознан."""
    contact = clean_text(value)
    if not contact or len(contact) > CONTACT_MAX:
        return None
    if _PHONE_RE.match(contact):
        return normalize_phone(contact)
    if _EMAIL_RE.match(contact):
        return contact.lower()
    if _USERNAME_RE.match(contact):
        return contact
    return None
