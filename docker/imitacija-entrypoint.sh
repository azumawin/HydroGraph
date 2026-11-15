#!/bin/sh
# Turn SCENARIO/SPEED/DURATION/BP_DEMO_INTERVAL into an imitacija invocation
# against the backend container. Extra arguments from compose pass through.
set -eu

: "${SCENARIO:=badscenario1}"
: "${BACKEND_URL:=http://backend:8000}"
# Paired synthetic pressure trends every N simulated seconds, the default the
# Makefile also passes: the real protocol takes its first cuff reading 8
# simulated hours in (bp_session_start_s), which no demo waits for. 0 restores
# that schedule and leaves blood pressure at its boot value.
: "${BP_DEMO_INTERVAL:=5}"
# The same for blood sugar: the CGM's 5-minute sensor window puts its first
# completed result 343 simulated seconds in, so the chart holds one boot point
# until then. 0 restores that window.
: "${GLUCOSE_DEMO_INTERVAL:=5}"
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
[ "$BP_DEMO_INTERVAL" != "0" ] && set -- "$@" --bp-demo-interval "$BP_DEMO_INTERVAL"
[ "$GLUCOSE_DEMO_INTERVAL" != "0" ] &&
    set -- "$@" --glucose-demo-interval "$GLUCOSE_DEMO_INTERVAL"

echo "scenario=${SCENARIO} backend=${BACKEND_URL} speed=${SPEED:-from config}" \
    "bp_demo=${BP_DEMO_INTERVAL}s glucose_demo=${GLUCOSE_DEMO_INTERVAL}s" >&2
exec imitacija "$@"
