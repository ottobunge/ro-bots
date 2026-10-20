FROM python:3.13-slim

WORKDIR /app

COPY pyproject.toml ./
COPY src ./src

RUN pip install --no-cache-dir . \
    && mkdir -p /data/receipts /data/memory

# Runs as root because docker/compose file secrets bind root-owned 0600 and this
# compose version ignores uid/gid/mode overrides; the process only ever READS
# the secret file (never echoes or logs it) and the port maps to 127.0.0.1.

EXPOSE 8401

CMD ["uvicorn", "dashboard_webapp.main:app", "--host", "0.0.0.0", "--port", "8401"]
