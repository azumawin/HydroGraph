#!/bin/sh
# Turn SCENARIO/SPEED/DURATION into an imitacija invocation against the backend
# container. Any extra arguments from compose are passed through unchanged.
set -eu

: "${SCENARIO:=healthy}"
: "${BACKEND_URL:=http://backend:8000}"
CONFIG="${CONFIG:-config/${SCENARIO}.toml}"

if [ ! -f "$CONFIG" ]; then
    echo "unknown scenario '${SCENARIO}'; available:" >&2
    for available in config/*.toml; do
        echo "  $(basename "$available" .toml)" >&2
    done
    exit 2
fi

# Each scenario pins base_url to the host loopback, which inside a container
# points at the container itself. Replace that one key with the service name
# and leave every other setting as the scenario author wrote it. Bare keys must
# precede the first [table], so the replacement goes at the top.
{
    printf 'base_url = "%s"\n' "$BACKEND_URL"
    sed '/^[[:space:]]*base_url[[:space:]]*=/d' "$CONFIG"
} > /tmp/scenario.toml

set -- --config /tmp/scenario.toml "$@"
[ -n "${SPEED:-}" ] && set -- "$@" --speed "$SPEED"
[ -n "${DURATION:-}" ] && set -- "$@" --duration "$DURATION"

echo "scenario=${SCENARIO} backend=${BACKEND_URL} speed=${SPEED:-from config}" >&2
exec imitacija "$@"
