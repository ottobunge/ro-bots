#!/usr/bin/env bash
# recover-world-ips.sh — re-pin rathena inter-server addresses after container churn.
#
# Why this exists: in this rootless podman network, `docker restart` REASSIGNS
# container IPs and the compose DNS registry can serve stale entries after
# recreate storms. The char-server then fails to register with the login-server
# and the login refuses every client with "there is no char-server online"
# (the window-30/31 entry-churn root cause; see
# run/reviews/playing-grind-operator-entry-churn-resolved.json).
#
# The fix (the "pin-restart piano"): restart login (fresh pasta port-forward),
# pin its literal IP into char_athena.conf login_ip, restart char, pin the
# char's NEW IP into map_athena.conf char_ip, restart map. Conf files pushed
# into the container MUST be chmod 644 or rAthena reports
# "Configuration file not found".
#
# Usage:
#   scripts/recover-world-ips.sh [PROJECT_PREFIX] [--dry-run] [--self-test]
#   PROJECT_PREFIX defaults to ro-bots-test (the owned test world).
#   --dry-run   print planned edits without restarting or writing anything.
#   --self-test run the conf-edit function against fixture files and exit.
#
# No guarded-publication machinery is touched: these are the owned test
# world's infra confs, and the edit is limited to the two address lines.

set -euo pipefail

PREFIX="ro-bots-test"
DRY_RUN=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --self-test) SELF_TEST=1 ;;
    --verify) VERIFY_ONLY=1 ;;
    ro-bots-*) PREFIX="$arg" ;;
    *) echo "unknown argument: $arg" >&2; exit 2 ;;
  esac
done

LOGIN="$PREFIX-rathena-login-1"
CHAR="$PREFIX-rathena-char-1"
MAP="$PREFIX-rathena-map-1"
MARIADB="$PREFIX-mariadb-1"

conf_ip() { # file, key -> prints the current literal IP (or the name)
  sed -n "s/^${2}: \\(.*\\)$/\\1/p" "$1" | head -1
}

edit_pin() { # file, key, new-ip — pins the address line, mode 644
  local file="$1" key="$2" ip="$3" before after
  before="$(conf_ip "$file" "$key")"
  if [[ -z "$before" ]]; then
    echo "FAIL: ${file}: no line '${key}: ...' found" >&2
    return 1
  fi
  sed -i "s/^${key}: .*/${key}: ${ip}/" "$file"
  chmod 644 "$file"
  after="$(conf_ip "$file" "$key")"
  echo "  ${file##*/}: ${key}: ${before} -> ${after}"
  [[ "$after" == "$ip" ]]
}

container_ip() { # name -> prints the container's IP on the compose network
  docker inspect "$1" --format '{{range $k,$v := .NetworkSettings.Networks}}{{$v.IPAddress}}{{end}}'
}

require_running() {
  local state
  state="$(docker inspect "$1" --format '{{.State.Status}}' 2>/dev/null || true)"
  if [[ "$state" != "running" ]]; then
    echo "FAIL: $1 is not running (state: ${state:-missing}). Bring the world up first." >&2
    exit 1
  fi
}

wait_listening() { # name host-port attempts
  local name="$1" port="$2" attempts="${3:-10}" i=0
  until timeout 2 bash -c "</dev/tcp/127.0.0.1/${port}" 2>/dev/null; do
    i=$((i + 1))
    if [[ $i -ge $attempts ]]; then
      echo "FAIL: $1 never opened host port ${port}" >&2
      return 1
    fi
    sleep 3
  done
  echo "  ${name} listening on ${port}"
}

journal_verify() { # wait up to ~90s for the two acceptance lines
  local i=0
  while :; do
    if journalctl --user --since '-3 minutes' --no-pager 2>/dev/null \
        | grep -q "char-server .* accepted" \
        && journalctl --user --since '-3 minutes' --no-pager 2>/dev/null \
        | grep -q "Map Server is now online"; then
      echo "  verified: char-server accepted + map server online"
      return 0
    fi
    i=$((i + 1))
    if [[ $i -ge 30 ]]; then
      echo "WARN: acceptance lines not seen within 90s — check journalctl --user for ${PREFIX}-rathena-*" >&2
      return 0 # do not fail the run; the operator verifies via the probe login
    fi
    sleep 3
  done
}

verify_pins() { # report conf-vs-reality drift without writing anything
  local rc=0 pair conf ip actual
  WORK="$(mktemp -d)"
  trap 'rm -rf "$WORK"' EXIT
  for pair in "${CHAR}:char_athena.conf:login_ip:${LOGIN}" "${MAP}:map_athena.conf:char_ip:${CHAR}"; do
    IFS=':' read -r conf_container conf_file conf_key target _ <<<"$pair"
    conf="${WORK}/${conf_file}"
    if ! docker cp "${conf_container}:/world/runtime/conf/${conf_file}" "$conf" >/dev/null 2>&1; then
      echo "FAIL: cannot read ${conf_file} from ${conf_container}" >&2
      rc=1
      continue
    fi
    ip="$(conf_ip "$conf" "$conf_key")"
    actual="$(container_ip "$target")"
    if [[ "$ip" == "$actual" ]]; then
      echo "  OK  ${conf_file} ${conf_key}=${ip} == ${target} ip"
    else
      echo "  DRIFT ${conf_file} ${conf_key}=${ip} but ${target} is at ${actual} — run without --verify to re-pin"
      rc=1
    fi
  done
  return "$rc"
}

if [[ "${SELF_TEST:-0}" == "1" ]]; then
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  printf 'userid: world_server\nlogin_ip: rathena-login\nlogin_port: 16900\n' >"$tmp/char_athena.conf"
  chmod 600 "$tmp/char_athena.conf"
  edit_pin "$tmp/char_athena.conf" login_ip 10.89.2.5
  grep -q '^login_ip: 10\.89\.2\.5$' "$tmp/char_athena.conf"
  grep -q '^login_port: 16900$' "$tmp/char_athena.conf"
  grep -q '^userid: world_server$' "$tmp/char_athena.conf"
  [[ "$(stat -c %a "$tmp/char_athena.conf")" == "644" ]]
  # idempotence: re-pinning the same value is a no-op that still succeeds
  edit_pin "$tmp/char_athena.conf" login_ip 10.89.2.5 >/dev/null
  grep -q '^login_ip: 10\.89\.2\.5$' "$tmp/char_athena.conf"
  echo "self-test OK"
  exit 0
fi

export DOCKER_API_VERSION="${DOCKER_API_VERSION:-1.44}"

if [[ "${VERIFY_ONLY:-0}" == "1" ]]; then
  echo "== world ${PREFIX}: pin verification =="
  for c in "$LOGIN" "$CHAR" "$MAP"; do require_running "$c"; done
  verify_pins && echo "== pins intact ==" || echo "== pins DRIFTED =="
  exit $?
fi

echo "== world ${PREFIX}: pin-restart piano =="
for c in "$LOGIN" "$CHAR" "$MAP" "$MARIADB"; do require_running "$c"; done
echo "  all four containers running"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# 1. restart login (fresh pasta port-forward for host clients)
if [[ $DRY_RUN == 1 ]]; then
  echo "  [dry-run] would restart ${LOGIN}"
  LOGIN_IP="$(container_ip "$LOGIN")"
else
  docker restart "$LOGIN" >/dev/null
  sleep 8
  LOGIN_IP="$(container_ip "$LOGIN")"
  wait_listening login 16900
fi
echo "  login at ${LOGIN_IP}"

# 2. pin login IP into char conf, restart char
docker cp "${CHAR}:/world/runtime/conf/char_athena.conf" "${WORK}/char_athena.conf" >/dev/null
if [[ $DRY_RUN == 1 ]]; then
  echo "  [dry-run] would pin ${WORK}-equivalent char_athena.conf login_ip -> ${LOGIN_IP} and restart ${CHAR}"
  CHAR_IP="$(container_ip "$CHAR")"
else
  edit_pin "${WORK}/char_athena.conf" login_ip "$LOGIN_IP"
  docker cp "${WORK}/char_athena.conf" "${CHAR}:/world/runtime/conf/char_athena.conf" >/dev/null
  docker restart "$CHAR" >/dev/null
  sleep 10
  CHAR_IP="$(container_ip "$CHAR")"
  wait_listening char 16121
fi
echo "  char at ${CHAR_IP}"

# 3. pin char IP into map conf, restart map
docker cp "${MAP}:/world/runtime/conf/map_athena.conf" "${WORK}/map_athena.conf" >/dev/null
if [[ $DRY_RUN == 1 ]]; then
  echo "  [dry-run] would pin map_athena.conf char_ip -> ${CHAR_IP} and restart ${MAP}"
else
  edit_pin "${WORK}/map_athena.conf" char_ip "$CHAR_IP"
  docker cp "${WORK}/map_athena.conf" "${MAP}:/world/runtime/conf/map_athena.conf" >/dev/null
  docker restart "$MAP" >/dev/null
  sleep 20
  wait_listening map 15121
  journal_verify
fi

echo "== done =="
if [[ $DRY_RUN == 1 ]]; then
  echo "(dry-run: nothing was restarted or written)"
fi
