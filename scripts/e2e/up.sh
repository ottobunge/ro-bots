#!/usr/bin/env bash
# e2e-up: bring up the CLEAN isolated e2e world (project ro-bots-e2e).
#
# Refuses unless EVERYTHING is fresh: no project containers, no volume, and all
# three host ports free. Creates the volume, imports the prepared runtime tree
# (uid 10000, the rathena-playable image's runtime uid), starts mariadb, waits
# for a REAL secret-authenticated query (the compose healthcheck can report
# unhealthy because healthcheck.sh ignores the password file), starts the three
# rathena roles (--no-deps: the mariadb health-gate is unreliable, see above),
# applies the scoped pin-restart piano, then verifies the world is REALLY up:
# journal acceptance lines + TCP connects + a live DB query. Never touches the
# ro-bots-test world.
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
# The chain must work on a fresh checkout: stage the private world on demand.
if ! e2e_load_inputs; then
  echo "== e2e-up: preparing the private stage (task e2e-prepare) =="
  "${SCRIPT_DIR}/prepare.sh"
  e2e_load_inputs
fi

echo "== e2e-up: clean-world preflight =="
if docker inspect "${E2E_DB_CONTAINER}" >/dev/null 2>&1 \
  || docker inspect "${E2E_MAP_CONTAINER}" >/dev/null 2>&1; then
  echo "e2e-up: REFUSED: project ${E2E_PROJECT} already has containers; run task e2e-down first" >&2
  exit 2
fi
if docker volume inspect "${WORLD_VOLUME}" >/dev/null 2>&1; then
  echo "e2e-up: REFUSED: volume ${WORLD_VOLUME} already exists; run task e2e-down first" >&2
  exit 2
fi
for port in "$WORLD_LOGIN_PORT" "$WORLD_CHAR_PORT" "$WORLD_MAP_PORT"; do
  if e2e_port_busy "$port"; then
    echo "e2e-up: REFUSED: host port ${port} is already in use" >&2
    exit 2
  fi
done
docker image inspect "${RATHENA_IMAGE}" >/dev/null 2>&1 || {
  echo "e2e-up: REFUSED: pinned image ${RATHENA_IMAGE} is not present locally" >&2
  exit 2
}
[[ -d "${WORLD_SCHEMA_DIR}" && -f "${WORLD_DB_ROOT_SECRET_FILE}" \
  && -f "${WORLD_DB_USER_SECRET_FILE}" ]] || {
  echo "e2e-up: REFUSED: stage schema/secrets missing under ${E2E_STAGE}" >&2
  exit 2
}

echo "== e2e-up: creating volume ${WORLD_VOLUME} =="
docker volume create "${WORLD_VOLUME}" >/dev/null

echo "== e2e-up: importing prepared runtime (uid 10000) =="
# The documented importer duties (world_prepare PENDING): runtime UID 10000
# (below) and SQL/DB read permissions — the mariadb entrypoint imports the
# schema as the container 'mysql' user (a host subuid), which cannot traverse
# the pipeline's 0700 stage dirs. Secrets stay 0600: mariadb reads them as
# container root, and host tooling runs as the owning user.
chmod o+rx "$(dirname -- "${WORLD_SCHEMA_DIR}")" "$(dirname -- "${WORLD_SCHEMA_DIR}")/.." \
  "${WORLD_SCHEMA_DIR}"
chmod 0644 "${WORLD_SCHEMA_DIR}"/*.sql
docker run --rm --entrypoint /bin/bash \
  -v "${WORLD_VOLUME}:/world" \
  -v "${WORLD_SCHEMA_DIR}/..:/stage:ro" \
  mariadb:11.4 -eu -c '
  mkdir -p /world/runtime /world/runtime/log /world/logs/rathena /world/memory/agents
  cp -a /stage/runtime/. /world/runtime/
  rm -rf /world/runtime/bin            # compose roles exec /libexec/rathena/<role>, not volume bin
  chown -R 10000:10000 /world/runtime /world/logs /world/memory
  chmod -R u=rwX,go-rwx /world/runtime /world/logs /world/memory
  ls /world/runtime
' | sed 's/^/  volume: /'

echo "== e2e-up: starting mariadb (fresh datadir imports ${WORLD_SCHEMA_DIR}) =="
e2e_compose up -d --no-build --pull never mariadb
DB_OK=0
for _ in $(seq 1 40); do
  if e2e_db_query "SELECT COUNT(*) FROM login;" >/dev/null 2>&1; then
    DB_OK=1
    break
  fi
  sleep 3
done
if [[ "$DB_OK" != 1 ]]; then
  echo "e2e-up: FAIL: mariadb never answered a secret-auth query" >&2
  docker logs --tail 15 "${E2E_DB_CONTAINER}" >&2 2>/dev/null || true
  exit 1
fi
echo "  mariadb answers (login rows: $(e2e_db_query 'SELECT COUNT(*) FROM login;'))"

echo "== e2e-up: starting rathena login/char/map (--no-deps) =="
e2e_compose up -d --no-build --pull never --no-deps rathena-login rathena-char rathena-map
for c in "$E2E_LOGIN_CONTAINER" "$E2E_CHAR_CONTAINER" "$E2E_MAP_CONTAINER"; do
  docker inspect "$c" --format '{{.State.Status}}' | grep -qx running || {
    echo "e2e-up: FAIL: $c is not running after up" >&2
    exit 1
  }
done

echo "== e2e-up: pin-restart piano (scoped to ${E2E_PROJECT}) =="
# The journal mark PRECEDES the piano: the final role restarts happen inside
# ips.sh, so their acceptance lines must stay inside the verification window.
JOURNAL_MARK="$(date '+%Y-%m-%d %H:%M:%S')"
"${SCRIPT_DIR}/ips.sh"

echo "== e2e-up: verifying the world is REALLY up =="
sleep 10
JOURNAL_OK=0
for _ in $(seq 1 40); do
  # Attribute each acceptance line to OUR container (the running ro-bots-test
  # world produces the same rAthena lines under its own identifiers).
  CHAR_OK="$(journalctl --user --since "${JOURNAL_MARK}" --no-pager 2>/dev/null \
    | grep -F "${E2E_LOGIN_CONTAINER}" | grep -c "char-server .* accepted" || true)"
  MAP_OK="$(journalctl --user --since "${JOURNAL_MARK}" --no-pager 2>/dev/null \
    | grep -F "${E2E_MAP_CONTAINER}" | grep -c "Map Server is now online" || true)"
  if [[ "${CHAR_OK:-0}" -ge 1 && "${MAP_OK:-0}" -ge 1 ]]; then
    JOURNAL_OK=1
    break
  fi
  sleep 5
done
if [[ "$JOURNAL_OK" != 1 ]]; then
  echo "e2e-up: FAIL: journal acceptance lines not seen after ${JOURNAL_MARK}" >&2
  journalctl --user --since "${JOURNAL_MARK}" --no-pager 2>/dev/null \
    | grep -E "${E2E_PROJECT}" | tail -20 >&2 || true
  exit 1
fi
echo "  journal: char-server accepted (login) + Map Server is now online (map)"
for port in "$WORLD_LOGIN_PORT" "$WORLD_CHAR_PORT" "$WORLD_MAP_PORT"; do
  e2e_port_busy "$port" || {
    echo "e2e-up: FAIL: host port ${port} does not accept connections" >&2
    exit 1
  }
  echo "  port ${port}: connect OK"
done
e2e_db_query "SELECT 1;" >/dev/null || {
  echo "e2e-up: FAIL: DB stopped answering" >&2
  exit 1
}
echo "e2e-up: world ${E2E_PROJECT} is up (volume ${WORLD_VOLUME}, ports ${WORLD_LOGIN_PORT}/${WORLD_CHAR_PORT}/${WORLD_MAP_PORT})"
