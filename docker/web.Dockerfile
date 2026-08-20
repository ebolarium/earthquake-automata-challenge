FROM python:3.11.11-slim-bookworm

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip install --no-cache-dir .

COPY configs ./configs
COPY data/manifests ./data/manifests
COPY scripts/generate_web_snapshot.py ./scripts/generate_web_snapshot.py
COPY web ./web

ENV PYTHONPATH=/app/src \
    HOST=0.0.0.0 \
    PORT=8080 \
    CATALOG_PATH=/data/california-earthquakes.sqlite \
    SNAPSHOT_PATH=/app/artifacts/web-v1/latest-forecast.json \
    GENERATE_SNAPSHOT=1

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/api/health', timeout=2)"

ENTRYPOINT ["sh", "web/entrypoint.sh"]
