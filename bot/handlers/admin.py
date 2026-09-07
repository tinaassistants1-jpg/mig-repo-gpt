"""Админские команды: просмотр заявок, смена статуса, статистика, выгрузка."""

from __future__ import annotations

from datetime import datetime

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import BufferedInputFile, Message

from bot import texts
from bot.catalog import budget_title, service_title
from bot.db.models import STATUS_TITLES, LeadStatus
from bot.db.repo import Repository
from bot.filters import IsAdmin
from bot.services.export import leads_to_csv

LEADS_LIMIT = 10
_STATUS_NAMES = ", ".join(status.value for status in LeadStatus)


def _parse_status(raw: str) -> LeadStatus | None:
    try:
        return LeadStatus(raw.strip().lower())
    except ValueError:
        return None


def _format_lead(lead) -> str:
    user = lead.user
    author = None
    if user is not None:
        author = f"@{user.username}" if user.username else f"id{user.telegram_id}"
    return texts.lead_card(
        lead_id=lead.id,
        service=service_title(lead.service),
        budget=budget_title(lead.budget),
        description=lead.description,
        contact_name=lead.contact_name,
        contact_value=lead.contact_value,
        status=STATUS_TITLES[lead.status],
        created_at=lead.created_at.strftime("%d.%m.%Y %H:%M") if lead.created_at else None,
        author=author,
    )


def build_router() -> Router:
    router = Router(name="admin")
    # Все хендлеры роутера доступны только администраторам.
    router.message.filter(IsAdmin())

    @router.message(Command("admin"))
    async def cmd_admin(message: Message) -> None:
        await message.answer(texts.ADMIN_HELP)

    @router.message(Command("leads"))
    async def cmd_leads(message: Message, command: CommandObject, repo: Repository) -> None:
        """/leads [статус] — последние заявки, при желании отфильтрованные."""
        status: LeadStatus | None = None
        if command.args:
            status = _parse_status(command.args)
            if status is None:
                await message.answer(texts.ERR_BAD_STATUS.format(statuses=_STATUS_NAMES))
                return

        leads = await repo.list_leads(limit=LEADS_LIMIT, status=status)
        if not leads:
            await message.answer(texts.NO_LEADS)
            return

        for lead in leads:
            await message.answer(_format_lead(lead))

    @router.message(Command("lead_info"))
    async def cmd_lead_info(message: Message, command: CommandObject, repo: Repository) -> None:
        if not command.args or not command.args.strip().isdigit():
            await message.answer(texts.ERR_BAD_USAGE.format(usage="/lead_info 12"))
            return

        lead = await repo.get_lead(int(command.args.strip()))
        if lead is None:
            await message.answer(texts.ERR_LEAD_NOT_FOUND.format(lead_id=command.args.strip()))
            return
        await message.answer(_format_lead(lead))

    @router.message(Command("status"))
    async def cmd_status(message: Message, command: CommandObject, repo: Repository) -> None:
        """/status <id> <new|in_work|done|rejected>"""
        parts = (command.args or "").split()
        if len(parts) != 2 or not parts[0].isdigit():
            await message.answer(texts.ERR_BAD_USAGE.format(usage="/status 12 in_work"))
            return

        lead_id = int(parts[0])
        status = _parse_status(parts[1])
        if status is None:
            await message.answer(texts.ERR_BAD_STATUS.format(statuses=_STATUS_NAMES))
            return

        if not await repo.set_status(lead_id, status):
            await message.answer(texts.ERR_LEAD_NOT_FOUND.format(lead_id=lead_id))
            return

        await repo.log_action(
            message.from_user.id,
            "admin",
            "lead_status_changed",
            f"новый статус: {status.value}",
            f"lead:{lead_id}",
        )
        await message.answer(f"Заявка №{lead_id}: статус → {STATUS_TITLES[status]}")

    @router.message(Command("stats"))
    async def cmd_stats(message: Message, repo: Repository) -> None:
        data = await repo.stats()
        lines = [
            "<b>Статистика</b>",
            f"Всего заявок: {data['total']}",
            f"Пользователей: {data['users']}",
            "",
        ]
        lines += [f"{STATUS_TITLES[status]}: {data[status.value]}" for status in LeadStatus]
        await message.answer("\n".join(lines))

    @router.message(Command("export"))
    async def cmd_export(message: Message, repo: Repository) -> None:
        leads = await repo.iter_all_leads()
        if not leads:
            await message.answer(texts.NO_LEADS)
            return

        filename = f"leads_{datetime.now():%Y%m%d_%H%M}.csv"
        document = BufferedInputFile(leads_to_csv(leads), filename=filename)
        await message.answer_document(document, caption=f"Выгружено заявок: {len(leads)}")
        await repo.log_action(
            message.from_user.id, "admin", "leads_exported", f"строк: {len(leads)}", filename
        )

    @router.message(Command("audit"))
    async def cmd_audit(message: Message, repo: Repository) -> None:
        records = await repo.recent_audit()
        if not records:
            await message.answer("Журнал пуст.")
            return

        lines = ["<b>Журнал действий</b>"]
        for record in records:
            when = record.created_at.strftime("%d.%m %H:%M") if record.created_at else "-"
            target = f" [{record.target}]" if record.target else ""
            lines.append(
                f"{when} · {record.actor_role} {record.actor_id} · "
                f"{record.action}{target} → {record.result}"
            )
        await message.answer("\n".join(lines))

    return router
