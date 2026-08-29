#!/bin/sh
set -e

if [ "${RUN_MIGRATIONS:-1}" = "1" ]; then
  uv run --no-sync alembic upgrade head
fi

exec "$@"
