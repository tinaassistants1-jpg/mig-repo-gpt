"""Разбор настроек из переменных окружения."""

from __future__ import annotations

import pytest

from bot.config import Settings


def _settings(**overrides) -> Settings:
    base = {"bot_token": "42:TEST-TOKEN"}
    return Settings(**{**base, **overrides})


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("111,222", [111, 222]),
        ("111, 222 ,333", [111, 222, 333]),
        ("111;222", [111, 222]),
        ("111", [111]),
        ("", []),
    ],
)
def test_admin_ids_from_string(raw: str, expected: list[int]) -> None:
    assert _settings(admin_ids=raw).admin_ids == expected


def test_empty_strings_become_none() -> None:
    settings = _settings(admin_ids="1", notify_chat_id="", redis_url="   ")
    assert settings.notify_chat_id is None
    assert settings.redis_url is None


def test_notify_targets_prefers_dedicated_chat() -> None:
    settings = _settings(admin_ids="1,2", notify_chat_id=-100500)
    assert settings.notify_targets == [-100500]


def test_notify_targets_fall_back_to_admins() -> None:
    settings = _settings(admin_ids="1,2")
    assert settings.notify_targets == [1, 2]


def test_is_admin() -> None:
    settings = _settings(admin_ids="1,2")
    assert settings.is_admin(1)
    assert not settings.is_admin(3)


def test_token_is_required() -> None:
    with pytest.raises(ValueError):
        Settings(bot_token="")
