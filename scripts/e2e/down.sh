#!/usr/bin/env bash
# e2e-down: tear the isolated e2e world down and VERIFY it is gone.
# Removes the compose project (containers + network) and the data volume.
# Tolerant of "nothing existed"; refuses to exit 0 while remnants remain.
# Never touches the ro-bots-test world (project name is e2e-only).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
if ! e2e_load_inputs; then
  echo "e2e-down: stage inputs missing; checking for leftover resources by name only"
  WORLD_VOLUME="${E2E_VOLUME}"
  # The compose file's ${VAR:?required} interpolations must still resolve.
  e2e_fallback_inputs
fi

echo "== e2e-down: project ${E2E_PROJECT} =="
e2e_compose down --remove-orphans 2>&1 | grep -v "^$" | sed 's/^/  /' || true

echo "== e2e-down: volume ${WORLD_VOLUME} =="
if docker volume inspect "${WORLD_VOLUME}" >/dev/null 2>&1; then
  docker volume rm "${WORLD_VOLUME}" >/dev/null
  echo "  removed"
else
  echo "  already absent"
fi

echo "== e2e-down: verifying everything is gone =="
LEFTOVER=0
if e2e_compose ps --format json 2>/dev/null | grep -vq '^\[\]$'; then
  echo "e2e-down: FAIL: compose still reports containers:" >&2
  e2e_compose ps -a >&2 || true
  LEFTOVER=1
fi
for c in "$E2E_LOGIN_CONTAINER" "$E2E_CHAR_CONTAINER" "$E2E_MAP_CONTAINER" "$E2E_DB_CONTAINER"; do
  if docker inspect "$c" >/dev/null 2>&1; then
    echo "e2e-down: FAIL: container $c still exists" >&2
    LEFTOVER=1
  fi
done
if docker volume ls --quiet --filter "name=^${WORLD_VOLUME}$" | grep -q .; then
  echo "e2e-down: FAIL: volume ${WORLD_VOLUME} still exists" >&2
  LEFTOVER=1
fi
for port in "$WORLD_LOGIN_PORT" "$WORLD_CHAR_PORT" "$WORLD_MAP_PORT"; do
  if e2e_port_busy "$port"; then
    echo "e2e-down: FAIL: host port ${port} still accepts connections" >&2
    LEFTOVER=1
  fi
done
if [[ "$LEFTOVER" != 0 ]]; then
  exit 1
fi
echo "e2e-down: project ${E2E_PROJECT} and volume ${WORLD_VOLUME} verified gone"
