# ro-bots web dashboard (agent tracking + run visibility)

FastAPI single-page dashboard over the experiment's read-only surfaces:

- the MariaDB `char`/`inventory` tables (agent/character state),
- the 30-minute window receipts (run records) at
  `.work/playing-grind-emission/evidence/receipt-*.json`,
- the WorldFeed event stream (FastAPI on port 8400),
- the per-agent memory directories (read-only listing).

This is the **Python web slice** inside `dashboard/webapp/`. The reviewed Rust
liveview dashboard lives at `dashboard/` top level (`dashboard/README.md`); it
is untouched and reads only the WorldFeed. The two overlap on host port 8401 —
run one at a time or override `DASHBOARD_PORT` here.

Read-only posture (v1): the DB connection opens with
`SET SESSION TRANSACTION READ ONLY` and every statement passes a
SELECT/SHOW/DESCRIBE allowlist; receipts and memory are mounted read-only; the
root password is read from the world's `secrets/db-root` file at runtime and is
never echoed, stored in reprs, or logged. `POST /api/agents/{id}/command` is a
stub: it queues in memory and answers `202` — no live agent delivery exists in
this slice.

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /api/agents` | agent/character list (char_id, name, class, base/job level, hp/sp, position, map, online) + latest goal/plan when the WorldFeed knows the persona |
| `GET /api/agents/{id}` | detail: inventory, stats, memory-view listing (files, sizes, mtimes) |
| `GET /api/agents/{id}/decisions?limit=N` | one agent's decision history aggregated across receipts, newest receipt first; each entry tagged with its `run_id` + receipt timestamp (`event`, `goal`, `plan_targets`, `actions`, `error_class`); `limit` default 100 (clamped to `[1, 1000]`), plus `runs_covered`; the receipt key `host_fixture_N` matches the char whose name ends in `_N` — receipts missing the tail or the agent are skipped |
| `GET /api/runs` | window receipts, newest first, pass/fail + headline counters (decisions, walks, attributed attacks, XP, engagement-floor met) |
| `GET /api/runs/{id}` | one receipt: per-agent counters, decide tail, script tail, move-gate reasons, gates, kill-commit block; bulky diagnostics are omitted (listed in `omitted`) |
| `GET /api/events?limit=N` | recent WorldFeed events (bounded SSE read; upstream failures degrade to `upstream.ok=false`, never a 500) |
| `POST /api/agents/{id}/command` | **stub**: validates `{"command": "..."}`, queues in memory, returns `202` with a `cmd-…` id (`GET /api/commands/{id}` shows the stub status) |
| `GET /` | single-page dashboard (vanilla JS, no build step): Agents/Runs/Agent views — hover an agent row for a popover (map+position, stats, inventory summary; detail cached 30s), click for the full agent tab with stats, inventory, memory and the decision-history table (limit selector 50/100/250) |
| `GET /api/health` | version + config echo (no secrets) |

A missing/degraded source answers honestly: `404` for unknown agent/run ids,
`503` when MariaDB or the receipts glob is unavailable, `200` with
`upstream.ok=false` for a dead feed — the runs panel stays usable without DB.

## Run (dev, nix toolchain)

From a checkout (or, from a linked worktree, point `nix develop` at the
canonical flake root):

```sh
nix develop   # or: nix develop --offline /home/otto/dev/ro-bots
cd dashboard/webapp
uv sync
RECEIPTS_GLOB=/abs/path/.work/playing-grind-emission/evidence/receipt-*.json \
WORLDFEED_URL=http://127.0.0.1:8400 \
  uv run python -m dashboard_webapp.main   # binds 127.0.0.1:8401
```

Without `DB_HOST` + `DB_ROOT_SECRET_FILE` the agent endpoints answer `503`
(honest degraded mode); runs and events work regardless.

## Run (docker compose)

```sh
cd dashboard/webapp
RECEIPTS_DIR=$PWD/../../.work/playing-grind-emission/evidence \
MEMORY_DIR=$PWD/../../run/worlds/test-first-live-86e7c36895db/memory \
DB_ROOT_SECRET_FILE=$PWD/../../run/worlds/test-first-live-86e7c36895db/secrets/db-root \
  docker compose -f docker-compose.dashboard.yml up --build
# dashboard on http://127.0.0.1:8401
```

The service joins the world stack's compose network (`WORLD_NETWORK`, default
`ro-bots-test_default`) so `mariadb` and `worldfeed` resolve by service name —
the world's MariaDB publishes no host port. Never put the password on the
command line or in the environment: compose reads the secret file path from
`DB_ROOT_SECRET_FILE` and mounts it under `/run/secrets/db-root`.

### Environment

| Variable | Default | Meaning |
| --- | --- | --- |
| `DASHBOARD_BIND` | `127.0.0.1:8401` | bind address (`0.0.0.0:8401` in compose) |
| `DASHBOARD_PORT` | `8401` | host port mapping in compose |
| `RECEIPTS_GLOB` | `.work/playing-grind-emission/evidence/receipt-*.json` | window receipts glob |
| `AGENT_MEMORY_ROOT` | *(unset)* | memory dir root for read-only per-agent listings |
| `WORLDFEED_URL` | `http://127.0.0.1:8400` | WorldFeed base URL |
| `EVENTS_DEADLINE_S` | `2.0` | bounded SSE read deadline |
| `DB_HOST`/`DB_PORT`/`DB_NAME`/`DB_USER` | unset/`3306`/`ragnarok`/`root` | MariaDB coordinates |
| `DB_ROOT_SECRET_FILE` | *(unset)* | secret file with the root password (read at runtime) |
| `WORLD_NETWORK` | `ro-bots-test_default` | external compose network to join |

## Tests (offline TDD)

The data layer sits behind a small repository interface
(`src/dashboard_webapp/repository.py`: `AgentSource`, `RunSource`,
`EventSource`, `GoalEnricher`); every test runs against fakes — no MariaDB, no
live WorldFeed, no receipts needed. The MariaDB source is exercised through an
injected fake connection (row mapping, connection kwargs, read-only guard); the
SSE reader through `httpx.MockTransport`.

```sh
cd dashboard/webapp
nix develop --offline /home/otto/dev/ro-bots -c bash -c \
  'cd dashboard/webapp && uv sync && uv run pytest'   # from a linked worktree
```

85 tests: config/secrets, receipt store (glob order, headline sums, schema
drift, path traversal), MariaDB source (SQL allowlist, mapping, connection
seam, secret handling), memory viewer, goal enrichment, SSE parsing, command
queue, all API endpoints (including the cross-receipt decision-history
aggregation: newest-first ordering, limit clamping/stops, missing tails,
missing agents, unreadable receipts, persona-index join), UI + health.

## Known v1 boundaries

- Commands are queued, not delivered — the wire-up to the live command seam is
  a later slice (the WorldFeed `POST /commands` endpoint is the natural target).
- Memory listing matches the character name in file paths; there is no
  authoritative char↔persona mapping in v1 (WorldFeed goal join uses persona
  name/id == character name).
- `GET /api/events` returns a bounded snapshot, not a live stream.
- Older window receipts legitimately lack tails/gates; the run detail renders
  them as empty ("not supplied") instead of failing.
