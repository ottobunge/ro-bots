# docker/ — ADR-010 worlds, volumes, and the e2e playground

## Quickstart

```bash
task e2e                                  # full-stack e2e on a clean test world
task playground                           # e2e + leave it up, then watch the dashboard
task world:up world=prod-myserver         # raise a named production world
task world:down world=debug               # stop a world (volume kept)
task world:wipe world=test                # wipe test world data (prod needs FORCE=1)
task world:status world=test              # services, volume, ports
```

Useful e2e env switches:

```bash
TICKS=60 task e2e                         # shorter run (default 120 simulated minutes)
KEEP=1 task e2e                           # leave the test world up afterwards
CLEF_URL=http://127.0.0.1:8300/v1/systemone task e2e   # real Clef, default is the stub
```

## Volume mapping (world isolation)

| WORLD_KIND | docker volume | compose project | lifecycle |
|---|---|---|---|
| `debug` (default) | `ro-bots-world-debug` | `ro-bots-debug` | live development; persists across restarts |
| `test` | `ro-bots-world-test` | `ro-bots-test` | **wiped + re-initialized on every e2e run** |
| `prod-<name>` | `ro-bots-world-prod-<name>` | `ro-bots-prod-<name>` | persists; never wiped by tests |

- The compose file templates the volume as `ro-bots-world-${WORLD_KIND:-debug}`.
- `scripts/world.sh up` creates the volume (`docker volume create`) before
  `compose up`; volumes are `external: true` in the compose file, so a
  `down -v` on one world can never touch another world's volume.
- All published ports bind `127.0.0.1` only: MariaDB 3306, login 6900,
  char 6121, map 5121, worldfeed 8400, dashboard 8401 (host) -> 8400.

## Prod-wipe protection

`task world:wipe world=prod-*` is structurally refused:

```
[world.sh] REFUSING to wipe world 'prod-myserver': prod worlds are
[world.sh]   never wiped by tests or scripts. This is structural
[world.sh]   protection (ADR-010). If you REALLY mean it:
[world.sh]   FORCE=1 task world:wipe world=prod-myserver
```

Only `FORCE=1` bypasses it, and the refusal lives in one place
(`scripts/world.sh`), not in anyone's shell history.

## What runs in containers today vs. natively (honest status)

| piece | status |
|---|---|
| MariaDB | **containerized** (`mariadb:11.4`, healthcheck, world volume) |
| worldfeed | **containerized**; the entry script runs the real `src/robots.adapters.worldfeed_server` when `src/` is importable, else a stdlib stub serving the same ADR-007 contract (graceful degradation, by design) |
| dashboard | **containerized** via the existing `dashboard/Dockerfile` (Rust multi-stage) |
| rAthena login/char/map | **natively today** (`spikes/002-rathena-up/start.sh`, ports 6900/6121/5121); `docker/rathena.Dockerfile` + the `rathena` compose profile exist as a documented follow-up — the image build (`PACKETVER=20180704`, PRERE, obfuscation off, PIN off, matching the spike) and the SQL-host entry script have not been validated end-to-end against a booted mariadb container yet |

The e2e (`scripts/e2e.sh`) reflects this: it brings up the containerized
world stack, then expects rAthena on localhost ports — starting it via the
native spike script when it isn't already listening, and exiting with a
clear graceful-skip reason when neither path is available. Containerized
rAthena lands when `docker compose --profile rathena up` is verified green;
no other file needs to change for that switch.

## Files

- `docker-compose.worlds.yml` — the world stack (templated volume, profiles)
- `docker/rathena.Dockerfile` + `docker/rathena-entry.sh` — containerized rAthena (follow-up)
- `docker/worldfeed.Dockerfile`, `docker/run_worldfeed.sh`, `docker/worldfeed_stub.py` — worldfeed with graceful degradation
- `scripts/world.sh` — up/down/wipe/status per WORLD_KIND
- `scripts/seed_test_agents.py` — deterministic seed (SQL + JSON manifest)
- `scripts/e2e.sh` / `scripts/e2e_runner.py` — the criterion-5 e2e
