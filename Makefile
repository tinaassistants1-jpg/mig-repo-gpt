.PHONY: help install run test lint fmt migrate revision up down logs backup

help:  ## Показать список команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:  ## Установить зависимости для разработки
	pip install -e ".[dev]"

run:  ## Запустить бота локально
	python -m bot

test:  ## Прогнать тесты
	pytest -q

lint:  ## Проверить стиль
	ruff check bot tests

fmt:  ## Отформатировать код
	ruff format bot tests && ruff check --fix bot tests

migrate:  ## Накатить миграции
	alembic upgrade head

revision:  ## Создать миграцию: make revision M="описание"
	alembic revision --autogenerate -m "$(M)"

up:  ## Поднять всё в Docker
	docker compose up -d --build

down:  ## Остановить контейнеры
	docker compose down

logs:  ## Логи бота
	docker compose logs -f bot

backup:  ## Резервная копия базы
	./scripts/backup_db.sh
