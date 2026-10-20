#!/usr/bin/env bash
# Pin-restart piano for the ISOLATED e2e world (project ro-bots-e2e).
#
# Copied pattern from scripts/recover-world-ips.sh (which is hardcoded to the
# ro-bots-test project and the 16900/16121/15121 ports and MUST NOT be modified
# in place). This copy is scoped to the e2e project and the 26900/26121/25121
# ports; nothing here touches ro-bots-test.
#
# Why: in this rootless podman network a `docker restart` REASSIGNS container
# IPs and compose DNS can serve stale entries, so after the first bring-up the
# inter-server addresses are pinned as literal IPs: restart login, pin its IP
# into char_athena.conf login_ip, restart char, pin the char's NEW IP into
# map_athena.conf char_ip, restart map. Conf files copied back MUST be mode 644
# or rAthena reports "Configuration file not found" (unreadable 0600 file).
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "${SCRIPT_DIR}/env.sh"
e2e_load_inputs
export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.44}"

conf_ip() { # file key
  sed -n "s/^${2}: \\(.*\\)$/\\1/p" "$1" | head -1
}

edit_pin() { # file key new-ip
  local file="$1" key="$2" ip="$3" before after
  before="$(conf_ip "$file" "$key")"
  [[ -n "$before" ]] || {
    echo "e2e-ips: ${file}: no line '${key}: ...' found" >&2
    return 1
  }
  sed -i "s/^${key}: .*/${key}: ${ip}/" "$file"
  chmod 644 "$file"
  after="$(conf_ip "$file" "$key")"
  echo "  ${file##*/}: ${key}: ${before} -> ${after}"
  [[ "$after" == "$ip" ]]
}

container_ip() {
  docker inspect "$1" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$v.IPAddress}}{{end}}'
}

require_running() {
  local state
  state="$(docker inspect "$1" --format '{{.State.Status}}' 2>/dev/null || true)"
  [[ "$state" == "running" ]] || {
    echo "e2e-ips: $1 is not running (state: ${state:-missing})" >&2
    return 1
  }
}

wait_listening() { # name host_port attempts
  local name="$1" port="$2" attempts="${3:-20}" i=0
  until timeout 2 bash -c "exec 3<>/dev/tcp/127.0.0.1/${port}" 2>/dev/null; do
    i=$((i + 1))
    if [[ $i -ge $attempts ]]; then
      echo "e2e-ips: FAIL: $1 never opened host port ${port}" >&2
      return 1
    fi
    sleep 3
  done
  echo "  ${name} listening on ${port}"
}

for c in "$E2E_LOGIN_CONTAINER" "$E2E_CHAR_CONTAINER" "$E2E_MAP_CONTAINER"; do
  require_running "$c"
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1. restart login (fresh pasta port-forward for host clients)
docker restart "$E2E_LOGIN_CONTAINER" >/dev/null
sleep 8
LOGIN_IP="$(container_ip "$E2E_LOGIN_CONTAINER")"
wait_listening login "$WORLD_LOGIN_PORT" 20
echo "  login at ${LOGIN_IP}"

# 2. pin login IP into char conf, restart char
docker cp "${E2E_CHAR_CONTAINER}:/world/runtime/conf/char_athena.conf" "${WORK}/char_athena.conf" >/dev/null
edit_pin "${WORK}/char_athena.conf" login_ip "$LOGIN_IP"
docker cp "${WORK}/char_athena.conf" "${E2E_CHAR_CONTAINER}:/world/runtime/conf/char_athena.conf" >/dev/null
docker restart "$E2E_CHAR_CONTAINER" >/dev/null
sleep 10
CHAR_IP="$(container_ip "$E2E_CHAR_CONTAINER")"
wait_listening char "$WORLD_CHAR_PORT" 20
echo "  char at ${CHAR_IP}"

# 3. pin char IP into map conf, restart map
docker cp "${E2E_MAP_CONTAINER}:/world/runtime/conf/map_athena.conf" "${WORK}/map_athena.conf" >/dev/null
edit_pin "${WORK}/map_athena.conf" char_ip "$CHAR_IP"
docker cp "${WORK}/map_athena.conf" "${E2E_MAP_CONTAINER}:/world/runtime/conf/map_athena.conf" >/dev/null
docker restart "$E2E_MAP_CONTAINER" >/dev/null
sleep 20
wait_listening map "$WORLD_MAP_PORT" 30

echo "e2e-ips: pins applied for ${E2E_PROJECT}"
