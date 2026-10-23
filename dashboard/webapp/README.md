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

Read-only posture for *observation* (the DB connection opens
`SET SESSION TRANSACTION READ ONLY` and every statement passes a
SELECT/SHOW/DESCRIBE allowlist; receipts and memory are mounted read-only; the
root password is read from the world's `secrets/db-root` file at runtime and is
never echoed, stored in reprs, or logged).

## Control plane (operator)

Three write surfaces, all deliberately narrow:

1. `POST /api/population` — body is the PopulationSpec
   (`{"world", "friend_groups", "friends_per_group": [min, max], "solo_agents",
   "seed"}`). Runs the real deterministic generator (`robots.popgen`) and writes
   `manifest.json` + `population.json` + `fixture.sql` into a fresh
   `run/worlds/<world>/population/<pop-…>/` directory. Returns `201` with the
   counts, the absolute paths and the generated `fixture_sql`. No DB write
   happens here; the world directory must already exist.
2. `POST /api/population/{id}/apply` — body `{"world"}`. Applies the stored
   fixture through the narrow writer: every statement must be `INSERT INTO`
   `login`/`char`/`skill` (the fixture's leading `USE ragnarok` is recognised
   and skipped); anything else is refused with `403` *before* a connection is
   opened (`SqlNotAllowed`). Connection = secret-file credentials + autocommit,
   write-capable (the write-side twin of the read-only source). Returns the
   account/character/statement counts.
3. `POST /api/agents/{id}/command` — allowlisted operator commands only:
   `say <text>` and `goal <grind|farm_item|idle_town|quest|social>`; anything
   else is `422` and nothing is persisted. The command is appended to
   `commands.jsonl` under `COMMAND_RUNTIME_ROOT`
   (default `.work/runtime/ro-bots-test/commands/`) and `202` returns the
   command id.

Command round-trip (dashboard → host → status):

```
POST /api/agents/150001/command {"command": "say hello"}
  -> 202 {"id": "cmd-…", "kind": "say", "text": "hello", …}
     runtime/commands/commands.jsonl += {"id","queued_ts","agent_id","char_name","kind","text","status":"queued"}
host tick (python -m robots.playing --command-root <runtime dir>):
  robots.app.command_poller.poll_once(host, runtime_dir)
    -> drain_commands() yields the unreceipted lines (non-allowlisted kind = loud error)
    -> say: host chat dispatcher (same admission path as WorldFeed POST /commands; offline agent = failed receipt)
    -> goal: persona goal override (applies even while offline)
    -> receipts.jsonl += {"id","applied_ts","ok","detail"}
GET /api/commands/cmd-…  -> {"status": "applied", "applied_ts": …}   (queued until the receipt lands)
```

The agent row's command box validates the allowlist client-side, then polls the
status endpoint and flips its button to **applied** when the receipt arrives.

## Operator: generate a population from the browser

1. Start the dashboard with `WORLDS_ROOT` pointing at the repo's `run/worlds`
   (the compose file mounts it at `/data/worlds` and the dev default is
   `run/worlds` relative to the process cwd) and `DB_*` configured.
2. Open the **Population** tab, fill in friend groups / per-group range /
   solo agents / seed, and press **POST /api/population** — the result panel
   shows counts, artifact paths and the fixture SQL.
3. Press **apply to world DB** (or `POST /api/population/{id}/apply`) to create
   the actual accounts/characters in the world's MariaDB.
4. Point a host at the generated population: the new
   `run/worlds/<world>/population/<id>/manifest.json` is a host-manifest, and
   the sibling `population.json` `schedules` mapping is its `--schedule-file`.
   Launch the host with `python -m robots.playing --manifest <that manifest>
   --command-root <COMMAND_RUNTIME_ROOT dir> …` so the dashboard's command box
   reaches live agents.

## Endpoints

| Route | Purpose |
| --- | --- |
| `GET /api/agents` | agent/character list (char_id, name, class, base/job level, hp/sp, position, map, online) + latest goal/plan when the WorldFeed knows the persona |
| `GET /api/agents/{id}` | detail: inventory, stats, memory-view listing (files, sizes, mtimes) |
| `GET /api/agents/{id}/decisions?limit=N` | one agent's decision history aggregated across receipts, newest receipt first; each entry tagged with its `run_id` + receipt timestamp (`event`, `goal`, `plan_targets`, `actions`, `error_class`); `limit` default 100 (clamped to `[1, 1000]`), plus `runs_covered`; the receipt key `host_fixture_N` matches the char whose name ends in `_N` — receipts missing the tail or the agent are skipped |
| `GET /api/runs` | window receipts, newest first, pass/fail + headline counters (decisions, walks, attributed attacks, XP, engagement-floor met) |
| `GET /api/runs/{id}` | one receipt: per-agent counters, decide tail, script tail, move-gate reasons, gates, kill-commit block; bulky diagnostics are omitted (listed in `omitted`) |
| `GET /api/events?limit=N` | recent WorldFeed events (bounded SSE read; upstream failures degrade to `upstream.ok=false`, never a 500) |
| `POST /api/agents/{id}/command` | allowlisted operator command (`say <text>` / `goal <goal>`), persists to `commands.jsonl`, returns `202` with a `cmd-…` id; non-allowlisted input is `422` |
| `GET /api/commands/{id}` | command status: `queued` until the host poller's receipt lands, then `applied` (+ `applied_ts`) |
| `POST /api/population` | generate a population (PopulationSpec + world name); `201` with counts, paths, fixture_sql |
| `POST /api/population/{id}/apply` | apply the stored fixture via the allowlisted writer; `403` on non-allowlisted SQL, `404` unknown world/population |
| `GET /` | single-page dashboard (vanilla JS, no build step): Agents/Runs/Population/Agent views — hover an agent row for a popover (map+position, stats, inventory summary; detail cached 30s), click for the full agent tab with stats, inventory, memory, the decision-history table (limit selector 50/100/250) and the History section (kind-filter chips, newest-first timeline, Combat + Plans sub-tabs, manual refresh + “older ↑” cursor paging) |
| `GET /api/agents/{id}/history` | per-agent timeline over the JSONL traces (persona via the host manifest): `?kinds=a,b` (default action_executed, world_event, chat_sent, chat_heard, goal_review, plan_authored, decide_response), `?limit=N` (default 200, cap 2000), `?before=<ISO>` cursor pages strictly older; newest-first compact rows (t, kind, map/x/y, summary); `200` with empty lists when traces are absent/unconfigured, `404` unknown agent, `422` bad kinds/before |
| `GET /api/agents/{id}/combat` | per-monster aggregation over the same traces (MonsterSpotted/DamageTaken + Attack actions): encounters (>300s gap = new encounter), attacks, damage taken totals, first/last seen |
| `GET /api/agents/{id}/plans` | goal_review/plan_authored timeline: goal, previous_goal, trigger, farm targets, newest first |
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
| `TRACES_DIR` | `.work/runtime/population-live/traces` | per-agent JSONL trace dir (read-only; backs the history/combat/plans endpoints) |
| `HOST_MANIFEST` | `.work/runtime/population-live/host-manifest.json` | host manifest mapping persona_id <-> char_name for the history endpoints |
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

196 tests: config/secrets, receipt store (glob order, headline sums, schema
drift, path traversal), MariaDB source (SQL allowlist, mapping, connection
seam, secret handling), memory viewer, goal enrichment, SSE parsing, the JSONL
command queue + say/goal allowlist, the population endpoints + the real
`robots.popgen` generator, the fixture applier + write allowlist guard, the
per-agent trace history (persona mapping, kind/limit/cursor, combat
aggregation, plans timeline — against fixture JSONL files, never the live
traces), and all API endpoints (including the cross-receipt decision-history
aggregation and the dashboard→poller command round-trip against the real
poller), UI + health.

## Known boundaries

- Command delivery requires a host running with `--command-root`; until one
  polls the runtime dir, commands stay `queued` (they persist and are applied
  on the next host tick).
- `POST /api/population` never touches the DB; applying the fixture is the
  separate allowlisted `…/apply` step, and it writes only `login`/`char`/
  `skill` INSERTs.
- Memory listing matches the character name in file paths; for the history
  endpoints the char↔persona mapping comes from the host manifest
  (`HOST_MANIFEST`), falling back to persona-id == trace file name.
- `GET /api/events` returns a bounded snapshot, not a live stream.
- Older window receipts legitimately lack tails/gates; the run detail renders
  them as empty ("not supplied") instead of failing.
