"""Конфигурация приложения: читается из переменных окружения / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки бота. Все значения приходят из окружения, секретов в коде нет."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    bot_token: str = Field(..., min_length=10)
    admin_ids: list[int] = Field(default_factory=list)
    notify_chat_id: int | None = None

    database_url: str = "sqlite+aiosqlite:///./leadbot.sqlite3"
    redis_url: str | None = None

    log_level: str = "INFO"
    throttle_rate: float = 0.5

    @field_validator("admin_ids", mode="before")
    @classmethod
    def _parse_admin_ids(cls, value: object) -> object:
        """Принимает как список, так и строку вида "111,222"."""
        if isinstance(value, str):
            return [int(part) for part in value.replace(";", ",").split(",") if part.strip()]
        return value

    @field_validator("notify_chat_id", "redis_url", mode="before")
    @classmethod
    def _empty_to_none(cls, value: object) -> object:
        """Пустая строка в .env означает «не задано»."""
        if isinstance(value, str) and not value.strip():
            return None
        return value

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admin_ids

    @property
    def notify_targets(self) -> list[int]:
        """Куда слать уведомления о новой заявке."""
        if self.notify_chat_id is not None:
            return [self.notify_chat_id]
        return list(self.admin_ids)


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
