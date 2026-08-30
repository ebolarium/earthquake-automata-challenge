#!/bin/sh
set -eu

python scripts/verify_prospective_protocol.py

if [ "${AUTO_MIGRATE:-1}" = "1" ]; then
  python scripts/migrate_database.py
fi

if [ "${VERIFY_OBJECT_STORAGE:-0}" = "1" ]; then
  python scripts/verify_object_storage.py
fi

exec python -m etas_challenge.worker_service
