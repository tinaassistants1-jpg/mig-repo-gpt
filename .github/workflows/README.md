# CI

`ci.yml` на каждый push и pull request:

- `ruff check` / `ruff format --check` — стиль и форматирование;
- `pytest` — 50 тестов, включая сквозной сценарий диалога;
- `alembic upgrade head` + `downgrade base` на SQLite — миграции накатываются и откатываются;
- `docker build` — образ собирается.

Секреты для CI не нужны: тесты используют подменённую Telegram-сессию и базу в памяти.
