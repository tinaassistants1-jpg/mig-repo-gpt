"""Репозиторий: вся работа с БД собрана здесь, хендлеры SQL не пишут."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import AuditLog, Lead, LeadStatus, User


@dataclass(frozen=True, slots=True)
class LeadDraft:
    """Собранные в диалоге данные заявки — до сохранения в БД."""

    service: str
    budget: str
    description: str
    contact_name: str
    contact_value: str


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Пользователи ──────────────────────────────────────────────────────

    async def upsert_user(
        self, telegram_id: int, username: str | None, full_name: str | None
    ) -> User:
        """Создать пользователя или обновить его профиль при каждом визите."""
        user = await self.session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, username=username, full_name=full_name)
            self.session.add(user)
            await self.session.flush()
            return user

        user.username = username
        user.full_name = full_name
        user.last_seen_at = datetime.now()
        await self.session.flush()
        return user

    # ── Заявки ────────────────────────────────────────────────────────────

    async def create_lead(self, user: User, draft: LeadDraft) -> Lead:
        lead = Lead(
            user_id=user.id,
            service=draft.service,
            budget=draft.budget,
            description=draft.description,
            contact_name=draft.contact_name,
            contact_value=draft.contact_value,
            status=LeadStatus.new,
        )
        self.session.add(lead)
        await self.session.flush()
        return lead

    async def get_lead(self, lead_id: int) -> Lead | None:
        return await self.session.scalar(select(Lead).where(Lead.id == lead_id))

    async def list_leads(
        self, limit: int = 10, offset: int = 0, status: LeadStatus | None = None
    ) -> list[Lead]:
        query = select(Lead).order_by(Lead.id.desc()).limit(limit).offset(offset)
        if status is not None:
            query = query.where(Lead.status == status)
        return list(await self.session.scalars(query))

    async def iter_all_leads(self) -> list[Lead]:
        """Все заявки по возрастанию id — для выгрузки в CSV."""
        return list(await self.session.scalars(select(Lead).order_by(Lead.id)))

    async def set_status(self, lead_id: int, status: LeadStatus) -> bool:
        """Сменить статус заявки. False — заявки с таким id нет."""
        result = await self.session.execute(
            update(Lead).where(Lead.id == lead_id).values(status=status)
        )
        return bool(result.rowcount)

    async def stats(self) -> dict[str, int]:
        """Счётчики по статусам плюс общее число заявок и пользователей."""
        rows = await self.session.execute(
            select(Lead.status, func.count(Lead.id)).group_by(Lead.status)
        )
        by_status = {status.value: count for status, count in rows.all()}
        result = {status.value: by_status.get(status.value, 0) for status in LeadStatus}
        result["total"] = sum(result.values())
        result["users"] = int(await self.session.scalar(select(func.count(User.id))) or 0)
        return result

    # ── Журнал ────────────────────────────────────────────────────────────

    async def log_action(
        self,
        actor_id: int,
        actor_role: str,
        action: str,
        result: str,
        target: str | None = None,
    ) -> None:
        self.session.add(
            AuditLog(
                actor_id=actor_id,
                actor_role=actor_role,
                action=action,
                target=target,
                result=result[:255],
            )
        )
        await self.session.flush()

    async def recent_audit(self, limit: int = 20) -> list[AuditLog]:
        return list(
            await self.session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(limit))
        )
