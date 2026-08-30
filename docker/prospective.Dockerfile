FROM python:3.11.11-slim-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir ".[prospective]"

COPY db ./db
COPY configs/prospective ./configs/prospective
COPY configs/regions ./configs/regions
COPY models ./models
COPY data/grids ./data/grids
COPY data/regions ./data/regions
COPY data/production ./data/production
COPY data/manifests/california-ch008-seed-20260819-v1.json ./data/manifests/california-ch008-seed-20260819-v1.json
COPY scripts/migrate_database.py ./scripts/migrate_database.py
COPY scripts/collect_prospective_catalogs.py ./scripts/collect_prospective_catalogs.py
COPY scripts/bootstrap_prospective_catalogs.py ./scripts/bootstrap_prospective_catalogs.py
COPY scripts/build_prospective_initial_states.py ./scripts/build_prospective_initial_states.py
COPY scripts/verify_prospective_initial_states.py ./scripts/verify_prospective_initial_states.py
COPY scripts/verify_prospective_bootstrap.py ./scripts/verify_prospective_bootstrap.py
COPY scripts/seed_prospective_database.py ./scripts/seed_prospective_database.py
COPY scripts/verify_object_storage.py ./scripts/verify_object_storage.py
COPY scripts/verify_prospective_protocol.py ./scripts/verify_prospective_protocol.py
COPY docker/prospective-entrypoint.sh ./docker/prospective-entrypoint.sh

ENV HOST=0.0.0.0 \
    PORT=8080 \
    AUTO_MIGRATE=1 \
    VERIFY_OBJECT_STORAGE=0 \
    REQUIRE_OBJECT_STORAGE=0

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=3)"

ENTRYPOINT ["sh", "docker/prospective-entrypoint.sh"]
