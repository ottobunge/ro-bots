#!/usr/bin/env bash
# Shared constants and helpers for the isolated e2e world (task e2e chain).
#
# ISOLATION CONTRACT: this world NEVER touches the running ro-bots-test world.
# - Its own compose project (ro-bots-e2e) and volume (ro-bots-e2e-world),
#   neither of which can collide with ro-bots-test / ro-bots-world-test.
# - Its own host ports 26900/26121/25121 (the test world uses 16900/16121/15121,
#   the debug defaults 6900/6121/5121).
# - Its own git-ignored stage under run/worlds/e2e/ (compose inputs, secrets,
#   fixture SQL, host manifest).
# The compose env ALWAYS carries RATHENA_IMAGE (required interpolation, pinned
# playable image). AGENT_IMAGE/DASHBOARD_IMAGE are interpolation-only
# placeholders: the e2e services list never creates those containers.
set -euo pipefail

E2E_REPO="$(git -C "$(dirname -- "${BASH_SOURCE[0]}")/.." rev-parse --show-toplevel)"
E2E_STAGE="${E2E_REPO}/run/worlds/e2e/e2e-isolated"
E2E_PROJECT="ro-bots-e2e"
E2E_VOLUME="ro-bots-e2e-world"
E2E_LOGIN_PORT="26900"
E2E_CHAR_PORT="26121"
E2E_MAP_PORT="25121"
E2E_LOGIN_CONTAINER="${E2E_PROJECT}-rathena-login-1"
E2E_CHAR_CONTAINER="${E2E_PROJECT}-rathena-char-1"
E2E_MAP_CONTAINER="${E2E_PROJECT}-rathena-map-1"
E2E_DB_CONTAINER="${E2E_PROJECT}-mariadb-1"
# The required pinned playable image (compose interpolation fails without it).
E2E_RATHENA_IMAGE="${E2E_RATHENA_IMAGE:-localhost/rathena-playable:20180704-e985006171d2}"
E2E_WORLDFEED_IMAGE="${E2E_WORLDFEED_IMAGE:-ro-bots/worldfeed:latest}"
# Interpolation-only placeholders; these services are never created here.
E2E_AGENT_IMAGE="${E2E_AGENT_IMAGE:-ro-bots/agent:e2e-placeholder-not-pulled}"
E2E_DASHBOARD_IMAGE="${E2E_DASHBOARD_IMAGE:-ro-bots/dashboard:e2e-placeholder-not-pulled}"
# Decision backend: the heavengraph Clef SystemOne endpoint (sub-second decides).
E2E_DECISION_URL="${E2E_DECISION_URL:-http://192.168.1.156:8091/v1/systemone}"
E2E_CHAT_URL="${E2E_CHAT_URL:-http://127.0.0.1:8300/v1/chat/completions}"
# Bounded verification pass (seconds). Hard ceiling: the e2e is a SHORT window.
E2E_DURATION_S="${E2E_DURATION_S:-300}"

e2e_compose() {
  docker compose --env-file /dev/null \
    -f "${E2E_REPO}/docker-compose.worlds.yml" \
    -p "${E2E_PROJECT}" "$@"
}

# Compose inputs for the selected world, exported into the process environment.
# The saved stage inputs are authoritative for kind/project/volume/ports/paths;
# they must match the constants above or the scripts refuse to run.
e2e_load_inputs() {
  local inputs="${E2E_STAGE}/compose-inputs.json"
  [[ -f "$inputs" ]] || {
    echo "e2e: missing stage inputs ${inputs}; run task e2e-prepare" >&2
    return 1
  }
  local key value
  while IFS=$'\t' read -r key value; do
    export "$key=$value"
  done < <("${E2E_REPO}/.venv/bin/python" - "$inputs" <<'PY'
import json, sys
data = json.load(open(sys.argv[1], encoding="utf-8"))
for key in sorted(data):
    if not key.startswith("COMPOSE_"):
        print(f"{key}\t{data[key]}")
PY
)
  local pair key expected_value
  for pair in \
    "WORLD_PROJECT:${E2E_PROJECT}" \
    "WORLD_VOLUME:${E2E_VOLUME}" \
    "WORLD_LOGIN_PORT:${E2E_LOGIN_PORT}" \
    "WORLD_CHAR_PORT:${E2E_CHAR_PORT}" \
    "WORLD_MAP_PORT:${E2E_MAP_PORT}"; do
    key="${pair%%:*}"
    expected_value="${pair#*:}"
    [[ "${!key}" == "$expected_value" ]] || {
      echo "e2e: stage input mismatch: ${key} is '${!key}', expected '${expected_value}'" >&2
      return 1
    }
  done
  export RATHENA_IMAGE="${E2E_RATHENA_IMAGE}"
  export WORLDFEED_IMAGE="${E2E_WORLDFEED_IMAGE}"
  export AGENT_IMAGE="${E2E_AGENT_IMAGE}"
  export DASHBOARD_IMAGE="${E2E_DASHBOARD_IMAGE}"
}

# Real secret-authenticated DB query; exit 1 unless the server answers.
# Usage: e2e_db_query "<SQL>"   (SQL must never embed secret material)
# -h 127.0.0.1 gates on REAL TCP readiness: the entrypoint's temporary init
# server is socket-only (skip-networking), so a socket query "succeeds" while
# the server rathena needs (TCP 3306) does not exist yet — the login-server
# then dies with 'Can't connect to server on mariadb (115)'.
e2e_db_query() {
  docker exec -e MYSQL_PWD="$(cat "${E2E_STAGE}/secrets/db-root")" \
    "${E2E_DB_CONTAINER}" mariadb -uroot -h 127.0.0.1 "${WORLD_DB_NAME:-ragnarok}" -N -B -e "$1" 2>/dev/null
}

e2e_port_busy() { # host_port -> 0 if something ACCEPTS connections
  timeout 2 bash -c "exec 3<>/dev/tcp/127.0.0.1/$1" 2>/dev/null
}

e2e_require_up() {
  docker inspect "${E2E_DB_CONTAINER}" \
    --format '{{.State.Status}}' 2>/dev/null | grep -qx running || {
    echo "e2e: world is not up (run task e2e-up first)" >&2
    return 1
  }
  e2e_db_query "SELECT 1;" >/dev/null || {
    echo "e2e: mariadb is running but does not answer a secret-auth query" >&2
    return 1
  }
}

# Compose-interpolation inputs for tooling that must run WITHOUT a prepared
# stage (e2e-down on a fresh checkout): every ${VAR:?required} reference in
# docker-compose.worlds.yml resolves, but nothing here starts any container.
e2e_fallback_inputs() {
  export WORLD_KIND="e2e"
  export WORLD_PROJECT="${E2E_PROJECT}"
  export WORLD_VOLUME="${E2E_VOLUME}"
  export WORLD_DB_NAME="ragnarok"
  export WORLD_DB_USER="ro_bots"
  export WORLD_SCHEMA_DIR="${E2E_STAGE}/sql"
  export WORLD_DB_ROOT_SECRET_FILE="${E2E_STAGE}/secrets/db-root"
  export WORLD_DB_USER_SECRET_FILE="${E2E_STAGE}/secrets/db-user"
  export WORLD_LOGIN_PORT="${E2E_LOGIN_PORT}"
  export WORLD_CHAR_PORT="${E2E_CHAR_PORT}"
  export WORLD_MAP_PORT="${E2E_MAP_PORT}"
  export RATHENA_IMAGE="${E2E_RATHENA_IMAGE}"
  export WORLDFEED_IMAGE="${E2E_WORLDFEED_IMAGE}"
  export AGENT_IMAGE="${E2E_AGENT_IMAGE}"
  export DASHBOARD_IMAGE="${E2E_DASHBOARD_IMAGE}"
}
