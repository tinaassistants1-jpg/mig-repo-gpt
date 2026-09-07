FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости ставим отдельным слоем — он переиспользуется между сборками.
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY bot ./bot
COPY migrations ./migrations
COPY alembic.ini ./
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh

# Контейнер работает не от root.
RUN useradd --create-home --uid 10001 botuser && chown -R botuser:botuser /app
USER botuser

ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "-m", "bot"]
