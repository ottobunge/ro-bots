"""Uvicorn entrypoint: ``uvicorn dashboard_webapp.main:app`` (or run directly)."""

from __future__ import annotations

import uvicorn

from dashboard_webapp.app import create_app_from_env
from dashboard_webapp.config import AppConfig

app = create_app_from_env()


def main() -> None:
    bind = AppConfig.from_env().bind
    host, _, port = bind.rpartition(":")
    uvicorn.run(app, host=host or "127.0.0.1", port=int(port or "8401"))


if __name__ == "__main__":
    main()
