"""Выгрузка заявок в CSV."""

from __future__ import annotations

import csv
import io

from bot.db.repo import LeadDraft, Repository
from bot.services.export import CSV_HEADERS, leads_to_csv


async def test_csv_contains_readable_titles(repo: Repository) -> None:
    user = await repo.upsert_user(555, "tina", "Тина К.")
    await repo.create_lead(
        user,
        LeadDraft(
            service="bot",
            budget="lt_50",
            description="Бот\nс переносом строки",
            contact_name="Тина",
            contact_value="@tina",
        ),
    )

    payload = leads_to_csv(await repo.iter_all_leads())
    assert payload.startswith(b"\xef\xbb\xbf"), "нужен BOM, иначе Excel ломает кириллицу"

    rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";"))
    assert tuple(rows[0]) == CSV_HEADERS

    row = dict(zip(CSV_HEADERS, rows[1], strict=True))
    assert row["услуга"] == "Телеграм-бот"
    assert row["бюджет"] == "до 50 000 ₽"
    assert row["username"] == "@tina"
    assert "\n" not in row["задача"]


async def test_empty_export_has_only_headers() -> None:
    payload = leads_to_csv([])
    rows = list(csv.reader(io.StringIO(payload.decode("utf-8-sig")), delimiter=";"))
    assert len(rows) == 1
