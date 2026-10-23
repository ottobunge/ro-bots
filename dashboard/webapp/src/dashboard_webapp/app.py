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
from dashboard_webapp.commands import (
    CommandNotAllowed,
    CommandQueue,
    JsonlCommandQueue,
    QueuedCommandNotFound,
    parse_command,
)
from dashboard_webapp.config import AppConfig
from dashboard_webapp.db_applier import DbApplier, SqlNotAllowed
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
from dashboard_webapp.population import (
    InvalidPopulationSpec,
    PopgenStore,
    PopulationNotFound,
    PopulationRequest,
    PopulationStore,
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
from dashboard_webapp.traces import (
    HISTORY_LIMIT_DEFAULT,
    InvalidHistoryQuery,
    TraceHistory,
    clamp_limit,
    parse_before,
    parse_kinds,
)

STATIC_DIR = Path(__file__).parent / "static"
_EVENTS_LIMIT_CAP = 200
_EVENTS_LIMIT_DEFAULT = 50
COMMAND_MAX_LENGTH = 500


class CommandIn(BaseModel):
    """Chat-command payload for the queued-command stub."""

    command: str = Field(min_length=1, max_length=COMMAND_MAX_LENGTH)


class ApplyRequest(BaseModel):
    """The world whose MariaDB the population fixture is applied to."""

    world: str = Field(min_length=1, max_length=64)


def _require(source: Any, what: str) -> Any:
    if source is None:
        raise DataSourceError(f"{what} not configured")
    return source


def _resolve_char_name(agents: AgentSource | None, char_id: int) -> str | None:
    """Best-effort char-name lookup so the host can resolve the persona."""
    if agents is None:
        return None
    return agents.agent_detail(char_id).agent.name


def create_app(
    *,
    agents: AgentSource | None,
    runs: RunSource | None,
    events: EventSource | None,
    commands: CommandQueue | None,
    goals: GoalEnricher | None,
    memory: MemoryViewerLike | None,
    population: PopulationStore | None = None,
    applier: DbApplier | None = None,
    traces: TraceHistory | None = None,
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

    @app.exception_handler(CommandNotAllowed)
    @app.exception_handler(InvalidPopulationSpec)
    async def _rejected_input(_request: Any, exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(PopulationNotFound)
    async def _unknown_population(_request: Any, exc: PopulationNotFound) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(SqlNotAllowed)
    async def _refused_sql(_request: Any, exc: SqlNotAllowed) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": str(exc)})

    @app.exception_handler(InvalidHistoryQuery)
    async def _bad_history_query(_request: Any, exc: InvalidHistoryQuery) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    def _char_name_lookup(agent_ref: str) -> str | None:
        """char-id -> char name through the agent source (best-effort)."""
        if agents is None or not agent_ref.isdigit():
            return None
        return agents.agent_detail(int(agent_ref)).agent.name

    def _agent_identity(agent_ref: str) -> dict[str, Any] | None:
        if agents is None or not agent_ref.isdigit():
            return None
        try:
            agent = agents.agent_detail(int(agent_ref)).agent
        except Exception:
            return None
        return {"char_id": agent.char_id, "name": agent.name}

    def _agent_exists(agent_ref: str) -> bool:
        """Does the agent source know this char id / name? (best-effort)"""
        if agents is None:
            return False
        try:
            if agent_ref.isdigit():
                agents.agent_detail(int(agent_ref))
                return True
            return any(a.name == agent_ref for a in agents.list_agents())
        except Exception:
            return False

    def _resolve_traced_agent(agent_ref: str) -> tuple[TraceHistory, str | None]:
        """The TraceHistory + persona for a dashboard agent id.

        An agent unknown to both the manifest and the agent source is 404; an
        agent that merely has no trace file resolves to persona None (the
        history endpoints then answer empty lists, never 404).
        """
        if traces is None:
            raise UnknownAgentError(f"trace history not configured: {agent_ref}")
        persona = traces.resolve_persona(agent_ref, char_lookup=_char_name_lookup)
        if persona is None and not _agent_exists(agent_ref):
            raise UnknownAgentError(f"unknown agent: {agent_ref}")
        return traces, persona

    def _history_source_meta(traces_src: TraceHistory | None, ok: bool) -> dict[str, Any]:
        if traces_src is None:
            return {"ok": False, "reason": "traces not configured"}
        return {"ok": ok, "dir": str(traces_src.traces_dir)}

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

    def _history_unconfigured() -> dict[str, Any]:
        return {
            "agent": None,
            "persona": None,
            "source": _history_source_meta(traces, ok=False),
        }

    @app.get("/api/agents/{agent_ref}/history")
    async def get_agent_history(
        agent_ref: str,
        kinds: str | None = None,
        limit: int = HISTORY_LIMIT_DEFAULT,
        before: str | None = None,
    ) -> dict[str, Any]:
        parsed_kinds = parse_kinds(kinds)  # InvalidHistoryQuery -> 422
        cursor = parse_before(before)
        if traces is None or not traces.configured():
            return {
                **_history_unconfigured(),
                "events": [],
                "count": 0,
                "limit": clamp_limit(limit),
                "next_before": None,
            }
        history_src, persona = _resolve_traced_agent(agent_ref)
        body = history_src.history(persona or "", kinds=parsed_kinds, limit=limit, before=cursor)
        return {
            "agent": _agent_identity(agent_ref),
            "persona": persona,
            **body,
            "source": _history_source_meta(traces, ok=True),
        }

    @app.get("/api/agents/{agent_ref}/combat")
    async def get_agent_combat(agent_ref: str) -> dict[str, Any]:
        if traces is None or not traces.configured():
            return {
                **_history_unconfigured(),
                "monsters": [],
                "engagements": 0,
                "attacks_total": 0,
                "damage_taken_total": 0,
            }
        history_src, persona = _resolve_traced_agent(agent_ref)
        body = history_src.combat(persona or "")
        return {
            "agent": _agent_identity(agent_ref),
            "persona": persona,
            **body,
            "source": _history_source_meta(traces, ok=True),
        }

    @app.get("/api/agents/{agent_ref}/plans")
    async def get_agent_plans(agent_ref: str, limit: int = HISTORY_LIMIT_DEFAULT) -> dict[str, Any]:
        if traces is None or not traces.configured():
            return {**_history_unconfigured(), "plans": [], "count": 0, "limit": clamp_limit(limit)}
        history_src, persona = _resolve_traced_agent(agent_ref)
        body = history_src.plans(persona or "", limit=limit)
        return {
            "agent": _agent_identity(agent_ref),
            "persona": persona,
            **body,
            "source": _history_source_meta(traces, ok=True),
        }

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
        kind, text = parse_command(payload.command)  # CommandNotAllowed -> 422
        char_name: str | None
        try:
            char_name = _resolve_char_name(agents, char_id)
        except UnknownAgentError:
            raise
        except Exception:
            char_name = None  # degraded source: queue anyway, host falls back to ids
        queued = queue.queue(agent_id=char_id, kind=kind, text=text, char_name=char_name)
        return {
            "id": queued.id,
            "status": queued.status,
            "agent_id": queued.agent_id,
            "kind": queued.kind,
            "text": queued.text,
            "note": "queued; the host command poller applies say/goal commands on its next tick",
        }

    @app.get("/api/commands/{command_id}")
    async def get_command(command_id: str) -> dict[str, Any]:
        queue = _require(commands, "command queue")
        queued = queue.status(command_id)
        return {
            "id": queued.id,
            "status": queued.status,
            "agent_id": queued.agent_id,
            "kind": queued.kind,
            "text": queued.text,
            "command": queued.command,
            "queued_ts": queued.queued_ts,
            "applied_ts": queued.applied_ts,
        }

    @app.post("/api/population", status_code=201)
    async def post_population(payload: PopulationRequest) -> dict[str, Any]:
        store = _require(population, "population store")
        artifact = store.generate(payload)
        return {
            "population_id": artifact.population_id,
            "world": artifact.world,
            "counts": artifact.counts,
            "paths": artifact.paths,
            "fixture_sql": artifact.fixture_sql,
        }

    @app.post("/api/population/{population_id}/apply")
    async def post_population_apply(population_id: str, payload: ApplyRequest) -> dict[str, Any]:
        db_applier = _require(applier, "db applier")
        result = db_applier.apply(payload.world, population_id)
        return {"status": "applied", **result}

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
                "worlds_root": cfg.worlds_root,
                "command_runtime_root": cfg.command_runtime_root,
                "traces_dir": cfg.traces_dir,
            },
        }

    @app.get("/")
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    return app


def create_app_from_env() -> FastAPI:
    """Real composition: MariaDB + receipts glob + WorldFeed + JSONL command queue."""
    cfg = AppConfig.from_env()

    agents = None
    applier = None
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

        from dashboard_webapp.db_applier import MariaDbFixtureApplier

        applier = MariaDbFixtureApplier(db, Path(cfg.worlds_root))

    from dashboard_webapp.events_source import SseEventSource
    from dashboard_webapp.goals_source import HttpGoalSource
    from dashboard_webapp.runs_store import ReceiptRunStore
    from dashboard_webapp.traces import TraceHistory

    return create_app(
        agents=agents,
        runs=ReceiptRunStore(cfg.receipts_glob),
        events=SseEventSource(cfg.worldfeed_url, deadline_s=cfg.events_deadline_s),
        commands=JsonlCommandQueue(Path(cfg.command_runtime_root)),
        goals=HttpGoalSource(cfg.worldfeed_url, timeout_s=cfg.events_deadline_s),
        memory=MemoryViewer(cfg.memory_root),
        population=PopgenStore(Path(cfg.worlds_root)),
        applier=applier,
        traces=TraceHistory(cfg.traces_dir, cfg.host_manifest),
        config=cfg,
    )
