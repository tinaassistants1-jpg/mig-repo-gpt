"""Проверки валидаторов ввода."""

import pytest

from bot.utils import validators


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("+7 (999) 123-45-67", "+79991234567"),
        ("8 999 123 45 67", "+79991234567"),
        ("79991234567", "+79991234567"),
        ("client@example.com", "client@example.com"),
        ("Client@Example.COM", "client@example.com"),
        ("@tina_manager", "@tina_manager"),
    ],
)
def test_valid_contacts(raw: str, expected: str) -> None:
    assert validators.validate_contact(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "позвоните мне", "@ab", "not-an-email@", "12345", "a" * 200],
)
def test_invalid_contacts(raw: str) -> None:
    assert validators.validate_contact(raw) is None


def test_name_is_trimmed() -> None:
    assert validators.validate_name("  Тина  ") == "Тина"


@pytest.mark.parametrize("raw", ["", "Т", "x" * (validators.NAME_MAX + 1)])
def test_invalid_names(raw: str) -> None:
    assert validators.validate_name(raw) is None


def test_description_too_short() -> None:
    assert validators.validate_description("коротко")[1] == "short"


def test_description_too_long() -> None:
    assert validators.validate_description("д" * 3000)[1] == "long"


def test_description_ok() -> None:
    value, error = validators.validate_description("  Нужен лендинг для студии  ")
    assert error is None
    assert value == "Нужен лендинг для студии"


def test_control_characters_are_stripped() -> None:
    assert validators.clean_text("плохой\x00ввод") == "плохойввод"
