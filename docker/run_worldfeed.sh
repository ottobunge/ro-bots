#!/usr/bin/env bash
# ADR-010: worldfeed entry point with graceful degradation.
# Tries the real WorldFeedServer (src/robots.adapters.worldfeed_server);
# if src/robots is not importable in this image/container, serves the stub.
set -u
PORT="${WORLDFEED_PORT:-8400}"

if python3 -c "import robots.adapters.worldfeed_server" >/dev/null 2>&1; then
  echo "[worldfeed] src/robots importable: serving the REAL WorldFeedServer on :$PORT"
  exec python3 - <<PY
import os, uvicorn
from robots.adapters.worldfeed_server import HOST, create_app, demo_world_state
uvicorn.run(create_app(demo_world_state()), host=HOST, port=int("$PORT"), log_level="info")
PY
else
  echo "[worldfeed] src/robots NOT importable: serving the STUB (same contract) on :$PORT"
  exec python3 /app/worldfeed_stub.py
fi
