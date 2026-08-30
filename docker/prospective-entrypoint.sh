#!/bin/sh
set -eu

if [ "${AUTO_MIGRATE:-1}" = "1" ]; then
  python scripts/migrate_database.py
fi

exec python -m etas_challenge.worker_service
