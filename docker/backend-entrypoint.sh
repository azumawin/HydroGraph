#!/bin/sh
# Prepare the database, then hand the container over to the server.
set -eu

: "${DJANGO_DB_PATH:=/data/db.sqlite3}"
export DJANGO_DB_PATH

mkdir -p "$(dirname "$DJANGO_DB_PATH")"

# A demo starts from an empty graph: drop the database unless RESET_DB=0 asks
# to keep what the previous run recorded. The -wal/-shm siblings belong to the
# same database, so leaving them behind would resurrect its last transactions.
if [ "${RESET_DB:-1}" = "1" ]; then
    rm -f "$DJANGO_DB_PATH" "$DJANGO_DB_PATH-wal" "$DJANGO_DB_PATH-shm"
    echo "reset: $DJANGO_DB_PATH" >&2
fi

python manage.py migrate --noinput

# --noreload: the autoreloader's second process would hold its own SSE streams.
exec python manage.py runserver 0.0.0.0:8000 --noreload
