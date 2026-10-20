"""Environment configuration + the secret-file pattern.

Credentials are read from files at runtime (docker/compose secrets or the
world secret dirs) and are never echoed into errors, reprs or logs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BIND = "127.0.0.1:8401"
DEFAULT_WORLDFEED_URL = "http://127.0.0.1:8400"
DEFAULT_RECEIPTS_GLOB = ".work/playing-grind-emission/evidence/receipt-*.json"
DEFAULT_WORLDS_ROOT = "run/worlds"
DEFAULT_COMMAND_RUNTIME_ROOT = ".work/runtime/ro-bots-test/commands"


class SecretFileError(Exception):
    """A secret file could not be read. The message names the path only."""


def read_secret(path: Path | str) -> str:
    """Read a secret file, stripping one trailing newline. Never log contents."""
    target = Path(path)
    try:
        return target.read_text(encoding="utf-8").rstrip("\r\n")
    except OSError as exc:
        raise SecretFileError(
            f"cannot read secret file: {target} ({exc.__class__.__name__})"
        ) from None


@dataclass(frozen=True)
class AppConfig:
    bind: str = DEFAULT_BIND
    worldfeed_url: str = DEFAULT_WORLDFEED_URL
    receipts_glob: str = DEFAULT_RECEIPTS_GLOB
    memory_root: str | None = None
    db_host: str | None = None
    db_port: int = 3306
    db_name: str = "ragnarok"
    db_user: str = "root"
    db_root_secret_file: str | None = None
    events_deadline_s: float = 2.0
    worlds_root: str = DEFAULT_WORLDS_ROOT
    command_runtime_root: str = DEFAULT_COMMAND_RUNTIME_ROOT

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> AppConfig:
        source = os.environ if env is None else env
        return cls(
            bind=source.get("DASHBOARD_BIND", DEFAULT_BIND),
            worldfeed_url=source.get("WORLDFEED_URL", DEFAULT_WORLDFEED_URL),
            receipts_glob=source.get("RECEIPTS_GLOB", DEFAULT_RECEIPTS_GLOB),
            memory_root=source.get("AGENT_MEMORY_ROOT"),
            db_host=source.get("DB_HOST"),
            db_port=int(source["DB_PORT"]) if "DB_PORT" in source else 3306,
            db_name=source.get("DB_NAME", "ragnarok"),
            db_user=source.get("DB_USER", "root"),
            db_root_secret_file=source.get("DB_ROOT_SECRET_FILE"),
            events_deadline_s=float(source.get("EVENTS_DEADLINE_S", "2.0")),
            worlds_root=source.get("WORLDS_ROOT", DEFAULT_WORLDS_ROOT),
            command_runtime_root=source.get("COMMAND_RUNTIME_ROOT", DEFAULT_COMMAND_RUNTIME_ROOT),
        )

    @property
    def db_configured(self) -> bool:
        return bool(self.db_host and self.db_root_secret_file)
