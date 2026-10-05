# ADR-010: worldfeed service image.
#
# Graceful degradation, documented: if `src/robots` is importable (repo
# mount or baked-in copy), the REAL WorldFeedServer serves the ADR-007
# contract on :8400. Otherwise the stub below serves the same JSON shape
# (roster/agent/events/commands) with empty data, so the dashboard and the
# e2e always have something to talk to.
FROM python:3.14-slim

WORKDIR /app

# Real server deps (fastapi/uvicorn). If src/robots cannot be imported the
# stub still runs: it only needs the stdlib http.server.
RUN pip install --no-cache-dir fastapi "uvicorn[standard]"

COPY docker/worldfeed_stub.py /app/worldfeed_stub.py
COPY docker/run_worldfeed.sh /app/run_worldfeed.sh
RUN chmod +x /app/run_worldfeed.sh

# src/ is mounted read-only by docker-compose.worlds.yml; the entry script
# tries the real server first, then falls back to the stub.
ENV WORLDFEED_PORT=8400
EXPOSE 8400
ENTRYPOINT ["/app/run_worldfeed.sh"]
