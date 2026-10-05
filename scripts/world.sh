#!/usr/bin/env bash
# ADR-010: world lifecycle helpers.
#
# A "world" is one isolated data space: MariaDB datadir + rAthena server
# state + agent persistence, all inside one named docker volume:
#
#   WORLD_KIND      volume                     compose project
#   -------------   -------------------------- ----------------------
#   debug           ro-bots-world-debug        ro-bots-debug
#   test            ro-bots-world-test         ro-bots-test
#   prod-<name>     ro-bots-world-prod-<name>  ro-bots-prod-<name>
#
# Usage: world.sh <up|down|wipe|status> [WORLD_KIND=...]
#   WORLD_KIND env var selects the world (default: debug).
#   FORCE=1 overrides the prod-* wipe protection (wipe only).
#
# Containerized rAthena (profiles: ["rathena"]) is a documented follow-up:
# until that image builds green, rAthena servers run NATIVELY via
# spikes/002-rathena-up/start.sh (this script prints the hint when the
# ports are expected but closed). MariaDB / worldfeed / dashboard are fully
# containerized today.
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$PROJ/docker-compose.worlds.yml"

WORLD_KIND="${WORLD_KIND:-debug}"
PROJECT="ro-bots-$WORLD_KIND"

case "$WORLD_KIND" in
  debug|test|prod-*) ;;
  *)
    echo "[world.sh] invalid WORLD_KIND '$WORLD_KIND' (debug | test | prod-NAME)" >&2
    exit 2
    ;;
esac

VOLUME="ro-bots-world-$WORLD_KIND"

compose() {
  docker compose -f "$COMPOSE_FILE" -p "$PROJECT" "$@"
}

ensure_volume() {
  if ! docker volume inspect "$VOLUME" >/dev/null 2>&1; then
    echo "[world.sh] creating volume $VOLUME for world '$WORLD_KIND'"
    docker volume create "$VOLUME" >/dev/null
  fi
}

cmd="${1:-status}"

case "$cmd" in
  up)
    ensure_volume
    WORLD_KIND="$WORLD_KIND" compose up -d
    echo "[world.sh] world '$WORLD_KIND' up (project $PROJECT, volume $VOLUME)"
    echo "[world.sh] rAthena services use the 'rathena' profile; without it,"
    echo "[world.sh]   run them natively: spikes/002-rathena-up/start.sh"
    ;;

  down)
    WORLD_KIND="$WORLD_KIND" compose down
    echo "[world.sh] world '$WORLD_KIND' down (volume $VOLUME kept)"
    ;;

  wipe)
    if [[ "$WORLD_KIND" == prod-* && "${FORCE:-0}" != "1" ]]; then
      echo "[world.sh] REFUSING to wipe world '$WORLD_KIND': prod worlds are" >&2
      echo "[world.sh]   never wiped by tests or scripts. This is structural" >&2
      echo "[world.sh]   protection (ADR-010). If you REALLY mean it:" >&2
      echo "[world.sh]   FORCE=1 task world:wipe world=$WORLD_KIND" >&2
      exit 3
    fi
    WORLD_KIND="$WORLD_KIND" compose down -v --remove-orphans
    docker volume rm "$VOLUME" >/dev/null 2>&1 || true
    echo "[world.sh] world '$WORLD_KIND' wiped (volume $VOLUME removed)"
    ;;

  status)
    echo "[world.sh] world:     $WORLD_KIND"
    echo "[world.sh] project:   $PROJECT"
    echo "[world.sh] volume:    $VOLUME $(docker volume inspect "$VOLUME" >/dev/null 2>&1 && echo exists || echo missing)"
    WORLD_KIND="$WORLD_KIND" compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null \
      || echo "[world.sh] (compose stack not running)"
    if [[ "$WORLD_KIND" == "test" ]]; then
      # e2e-relevant ports: closed is fine when rAthena runs natively elsewhere
      for p in 6900 6121 5121 8400; do
        if ss -tln "( sport = :$p )" 2>/dev/null | grep -q LISTEN; then
          echo "[world.sh] port $p: LISTENING"
        else
          echo "[world.sh] port $p: closed"
        fi
      done
    fi
    ;;

  *)
    echo "usage: world.sh {up|down|wipe|status}   (WORLD_KIND=debug|test|prod-NAME, FORCE=1 overrides prod-wipe protection)" >&2
    exit 2
    ;;
esac
