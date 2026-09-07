"""Модели данных.

Типы подобраны так, чтобы схема одинаково работала на PostgreSQL (прод) и
SQLite (тесты): вместо native enum — VARCHAR с проверкой на уровне приложения.
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LeadStatus(enum.StrEnum):
    """Жизненный цикл заявки."""

    new = "new"
    in_work = "in_work"
    done = "done"
    rejected = "rejected"


STATUS_TITLES: dict[LeadStatus, str] = {
    LeadStatus.new: "🆕 Новая",
    LeadStatus.in_work: "⏳ В работе",
    LeadStatus.done: "✅ Завершена",
    LeadStatus.rejected: "❌ Отклонена",
}


class User(Base):
    """Пользователь Telegram, который взаимодействовал с ботом."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    full_name: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    leads: Mapped[list[Lead]] = relationship(back_populates="user", lazy="selectin")


class Lead(Base):
    """Заявка, собранная в диалоге с клиентом."""

    __tablename__ = "leads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    service: Mapped[str] = mapped_column(String(32))
    budget: Mapped[str] = mapped_column(String(32))
    description: Mapped[str] = mapped_column(Text)
    contact_name: Mapped[str] = mapped_column(String(128))
    contact_value: Mapped[str] = mapped_column(String(128))

    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus, native_enum=False, length=16, values_callable=lambda e: [m.value for m in e]
        ),
        default=LeadStatus.new,
        index=True,
    )
    comment: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="leads", lazy="joined")


class AuditLog(Base):
    """Журнал действий: кто, что сделал, над чем и с каким результатом."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_id: Mapped[int] = mapped_column(BigInteger, index=True)
    actor_role: Mapped[str] = mapped_column(String(16))
    action: Mapped[str] = mapped_column(String(64), index=True)
    target: Mapped[str | None] = mapped_column(String(64))
    result: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
