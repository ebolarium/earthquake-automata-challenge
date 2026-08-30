FROM python:3.11.11-slim-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir ".[prospective]"

COPY db ./db
COPY scripts/migrate_database.py ./scripts/migrate_database.py
COPY docker/prospective-entrypoint.sh ./docker/prospective-entrypoint.sh

ENV HOST=0.0.0.0 \
    PORT=8080 \
    AUTO_MIGRATE=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

ENTRYPOINT ["sh", "docker/prospective-entrypoint.sh"]
