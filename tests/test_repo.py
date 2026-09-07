"""Репозиторий: сохранение заявок, статусы, статистика, журнал."""

from __future__ import annotations

import pytest

from bot.db.models import LeadStatus
from bot.db.repo import LeadDraft, Repository

DRAFT = LeadDraft(
    service="website",
    budget="50_150",
    description="Нужен лендинг для студии",
    contact_name="Тина",
    contact_value="+79991234567",
)


async def test_upsert_user_creates_once(repo: Repository) -> None:
    first = await repo.upsert_user(555, "tina", "Тина К.")
    second = await repo.upsert_user(555, "tina_new", "Тина К.")
    assert first.id == second.id
    assert second.username == "tina_new"


async def test_create_and_read_lead(repo: Repository) -> None:
    user = await repo.upsert_user(555, "tina", "Тина К.")
    lead = await repo.create_lead(user, DRAFT)

    stored = await repo.get_lead(lead.id)
    assert stored is not None
    assert stored.status is LeadStatus.new
    assert stored.description == DRAFT.description
    assert stored.user.telegram_id == 555


async def test_list_leads_is_newest_first(repo: Repository) -> None:
    user = await repo.upsert_user(555, "tina", "Тина К.")
    created = [await repo.create_lead(user, DRAFT) for _ in range(3)]

    listed = await repo.list_leads(limit=2)
    assert [lead.id for lead in listed] == [created[2].id, created[1].id]


async def test_status_filter(repo: Repository) -> None:
    user = await repo.upsert_user(555, "tina", "Тина К.")
    first = await repo.create_lead(user, DRAFT)
    await repo.create_lead(user, DRAFT)
    await repo.set_status(first.id, LeadStatus.done)

    done = await repo.list_leads(status=LeadStatus.done)
    assert [lead.id for lead in done] == [first.id]


async def test_set_status_on_missing_lead(repo: Repository) -> None:
    assert await repo.set_status(9999, LeadStatus.done) is False


async def test_stats(repo: Repository) -> None:
    user = await repo.upsert_user(555, "tina", "Тина К.")
    first = await repo.create_lead(user, DRAFT)
    await repo.create_lead(user, DRAFT)
    await repo.set_status(first.id, LeadStatus.in_work)

    stats = await repo.stats()
    assert stats["total"] == 2
    assert stats["users"] == 1
    assert stats["new"] == 1
    assert stats["in_work"] == 1
    assert stats["rejected"] == 0


async def test_audit_log(repo: Repository) -> None:
    await repo.log_action(555, "admin", "lead_status_changed", "новый статус: done", "lead:1")
    records = await repo.recent_audit()
    assert len(records) == 1
    assert records[0].action == "lead_status_changed"
    assert records[0].target == "lead:1"


@pytest.mark.parametrize("long_result", ["x" * 400])
async def test_audit_result_is_truncated(repo: Repository, long_result: str) -> None:
    await repo.log_action(555, "admin", "test", long_result)
    records = await repo.recent_audit()
    assert len(records[0].result) == 255
