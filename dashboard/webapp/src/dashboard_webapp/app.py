"""FastAPI app: endpoints over the small repository interface.

`create_app` takes injected sources (fakes in tests); `create_app_from_env`
builds the real composition from :class:`AppConfig`. Sources that raise
``UnknownAgentError``/``UnknownRunError`` answer 404, other ``DataSourceError``
answers 503 — a degraded source never crashes the dashboard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from dashboard_webapp import __version__
from dashboard_webapp.commands import CommandQueue, InMemoryCommandQueue, QueuedCommandNotFound
from dashboard_webapp.config import AppConfig
from dashboard_webapp.decisions import (
    DECISIONS_LIMIT_DEFAULT,
    agent_decision_history,
)
from dashboard_webapp.memory_view import MemoryViewer
from dashboard_webapp.models import (
    agent_json,
    event_json,
    inventory_json,
    memory_file_json,
    run_summary_json,
)
from dashboard_webapp.repository import (
    AgentSource,
    DataSourceError,
    EventSource,
    GoalEnricher,
    MemoryViewerLike,
    RunSource,
    UnknownAgentError,
    UnknownRunError,
)

STATIC_DIR = Path(__file__).parent / "static"
_EVENTS_LIMIT_CAP = 200
_EVENTS_LIMIT_DEFAULT = 50
COMMAND_MAX_LENGTH = 500


class CommandIn(BaseModel):
    """Chat-command payload for the queued-command stub."""

    command: str = Field(min_length=1, max_length=COMMAND_MAX_LENGTH)


def _require(source: Any, what: str) -> Any:
    if source is None:
        raise DataSourceError(f"{what} not configured")
    return source


def create_app(
    *,
    agents: AgentSource | None,
    runs: RunSource | None,
    events: EventSource | None,
    commands: CommandQueue | None,
    goals: GoalEnricher | None,
    memory: MemoryViewerLike | None,
    config: AppConfig | None = None,
) -> FastAPI:
    cfg = config or AppConfig()
    app = FastAPI(title="ro-bots dashboard", version=__version__, docs_url="/api/docs")

    @app.exception_handler(UnknownAgentError)
    @app.exception_handler(UnknownRunError)
    async def _unknown_resource(_request: Any, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(DataSourceError)
    async def _source_degraded(_request: Any, exc: DataSourceError) -> JSONResponse:
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(QueuedCommandNotFound)
    async def _unknown_command(_request: Any, exc: QueuedCommandNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.get("/api/agents")
    async def get_agents() -> dict[str, Any]:
        source = _require(agents, "agent source")
        summaries = source.list_agents()
        goals_error = None
        if goals is not None:
            try:
                summaries = goals.enrich(summaries)
            except Exception as exc:
                goals_error = str(exc)
        return {
            "agents": [agent_json(agent) for agent in summaries],
            "source": {"ok": True, "goals_error": goals_error},
        }

    @app.get("/api/agents/{char_id}")
    async def get_agent(char_id: int) -> dict[str, Any]:
        source = _require(agents, "agent source")
        detail = source.agent_detail(char_id)
        if memory is not None:
            files = [memory_file_json(item) for item in memory.list(detail.agent.name)]
            root = getattr(memory, "root", None) or detail.memory_root
        else:
            files = [memory_file_json(item) for item in detail.memory_files]
            root = detail.memory_root
        return {
            "agent": agent_json(detail.agent),
            "inventory": [inventory_json(item) for item in detail.inventory],
            "stats": detail.stats,
            "memory": {"root": root, "files": files},
        }

    @app.get("/api/agents/{char_id}/decisions")
    async def get_agent_decisions(
        char_id: int, limit: int = DECISIONS_LIMIT_DEFAULT
    ) -> dict[str, Any]:
        runs_source = _require(runs, "run source")
        agent_source = _require(agents, "agent source")
        return agent_decision_history(runs_source, agent_source, char_id, limit)

    @app.get("/api/runs")
    async def get_runs() -> dict[str, Any]:
        source = _require(runs, "run source")
        return {"runs": [run_summary_json(run) for run in source.list_runs()]}

    @app.get("/api/runs/{run_id}")
    async def get_run(run_id: str) -> dict[str, Any]:
        source = _require(runs, "run source")
        detail = source.run_detail(run_id)
        return {
            **run_summary_json(detail.summary),
            "agents": detail.agents,
            "meta": detail.meta,
            "omitted": detail.omitted,
        }

    @app.get("/api/events")
    async def get_events(limit: int = _EVENTS_LIMIT_DEFAULT) -> dict[str, Any]:
        source = _require(events, "event source")
        page = source.recent_events(max(1, min(limit, _EVENTS_LIMIT_CAP)))
        return {
            "events": [event_json(event) for event in page.events],
            "upstream": {"url": page.upstream_url, "ok": page.ok, "error": page.error},
        }

    @app.post("/api/agents/{char_id}/command", status_code=202)
    async def post_command(char_id: int, payload: CommandIn) -> dict[str, Any]:
        queue = _require(commands, "command queue")
        queued = queue.queue(agent_id=char_id, command=payload.command)
        return {
            "id": queued.id,
            "status": queued.status,
            "agent_id": queued.agent_id,
            "note": "stub: command queued only; not delivered to a live agent in this slice",
        }

    @app.get("/api/commands/{command_id}")
    async def get_command(command_id: str) -> dict[str, Any]:
        queue = _require(commands, "command queue")
        queued = queue.status(command_id)
        return {
            "id": queued.id,
            "status": queued.status,
            "agent_id": queued.agent_id,
            "command": queued.command,
            "queued_ts": queued.queued_ts,
        }

    @app.get("/api/health")
    async def health() -> dict[str, Any]:
        return {
            "status": "ok",
            "version": __version__,
            "config": {
                "bind": cfg.bind,
                "worldfeed_url": cfg.worldfeed_url,
                "receipts_glob": cfg.receipts_glob,
                "memory_root": cfg.memory_root,
                "db_configured": cfg.db_configured,
            },
        }

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    return app


def create_app_from_env() -> FastAPI:
    """Real composition: MariaDB + receipts glob + WorldFeed + stub queue."""
    cfg = AppConfig.from_env()

    agents = None
    if cfg.db_configured:
        from dashboard_webapp.mariadb_source import DbConfig, MariaDbAgentSource

        db = DbConfig(
            host=cfg.db_host or "",
            port=cfg.db_port,
            name=cfg.db_name,
            user=cfg.db_user,
            root_secret_file=cfg.db_root_secret_file or "",
        )
        agents = MariaDbAgentSource(db)

    from dashboard_webapp.events_source import SseEventSource
    from dashboard_webapp.goals_source import HttpGoalSource
    from dashboard_webapp.runs_store import ReceiptRunStore

    return create_app(
        agents=agents,
        runs=ReceiptRunStore(cfg.receipts_glob),
        events=SseEventSource(cfg.worldfeed_url, deadline_s=cfg.events_deadline_s),
        commands=InMemoryCommandQueue(),
        goals=HttpGoalSource(cfg.worldfeed_url, timeout_s=cfg.events_deadline_s),
        memory=MemoryViewer(cfg.memory_root),
        config=cfg,
    )
