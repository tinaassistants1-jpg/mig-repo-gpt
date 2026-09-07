"""Выгрузка заявок в CSV."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable

from bot.catalog import budget_title, service_title
from bot.db.models import Lead

CSV_HEADERS = (
    "id",
    "создана",
    "статус",
    "услуга",
    "бюджет",
    "имя",
    "контакт",
    "telegram_id",
    "username",
    "задача",
)


def leads_to_csv(leads: Iterable[Lead]) -> bytes:
    """Собрать CSV в кодировке UTF-8 с BOM — чтобы Excel открывал без бубна."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", quoting=csv.QUOTE_MINIMAL)
    writer.writerow(CSV_HEADERS)
    for lead in leads:
        user = lead.user
        writer.writerow(
            [
                lead.id,
                lead.created_at.strftime("%Y-%m-%d %H:%M") if lead.created_at else "",
                lead.status.value,
                service_title(lead.service),
                budget_title(lead.budget),
                lead.contact_name,
                lead.contact_value,
                user.telegram_id if user else "",
                f"@{user.username}" if user and user.username else "",
                lead.description.replace("\n", " "),
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")
