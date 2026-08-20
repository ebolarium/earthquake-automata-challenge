#!/bin/sh
set -eu

if [ "${GENERATE_SNAPSHOT:-1}" = "1" ] || [ ! -f "$SNAPSHOT_PATH" ]; then
  python scripts/generate_web_snapshot.py \
    --catalog "$CATALOG_PATH" \
    --output "$SNAPSHOT_PATH" \
    --manifest /tmp/web-snapshot-manifest.json
fi

exec python web/server.py \
  --host "${HOST:-0.0.0.0}" \
  --port "${PORT:-8080}" \
  --snapshot "$SNAPSHOT_PATH"
