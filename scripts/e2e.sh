#!/usr/bin/env bash
# ADR-010: e2e entry point (wraps scripts/e2e_runner.py).
#
#   task e2e                 # wipe + up + seed + bots + ticks + assertions
#   task e2e KEEP=1          # playground: leave the test world up
#   CLEF_URL=http://... task e2e   # real Clef instead of the stub
#   TICKS=60 task e2e        # fewer simulated minutes
#
# Python is the project venv when present (.venv), else whatever python3 is
# on PATH (stdlib-only fallback; the runner degrades gracefully).
set -euo pipefail

PROJ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ"

PY="$PROJ/.venv/bin/python"
[ -x "$PY" ] || PY="$(command -v python3)"

export TICKS="${TICKS:-120}"
export KEEP="${KEEP:-0}"
export CLEF_URL="${CLEF_URL:-}"

exec "$PY" scripts/e2e_runner.py
