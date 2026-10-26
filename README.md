# ro-bots

Experiment: a private **Ragnarok Online** server (rAthena) populated with server-side
bot players whose behavior is driven by **Clef**, a decision model, at every game tick —
with an LLM escalation path for complex actions and chat.

The thesis: a typed decision model (single forward pass, no text generation, calibrated
probabilities) can handle 95%+ of bot cognition — grinding, farming, idling in town,
taking level-appropriate quests, party/guild formation, premade chat phrases — and only
fall back to a generative LLM for free-form chat and complex decisions. Goal: measure
how fast and dynamic a "living" MMO world can be pushed on a single machine.

## Architecture

```
┌────────────────────────────────────────────────────────┐
│                    rAthena (C++)                        │
│   login:6900   char:6121   map:5121   + MariaDB        │
└──────▲───────────────────────────────▲─────────────────┘
       │ raw RO wire protocol          │ (same protocol)
       │ (clientless connections)      │
┌──────┴─────────────────────────────────────────────────┐
│                  Bot runtime (per bot)                  │
│  ┌───────────────┐    low-confidence / complex / chat  │
│  │ Clef decider  │──────────────┐                      │
│  │ (every tick:  │              ▼                      │
│  │ state + ~15   │    ┌──────────────────┐              │
│  │ noul/choice/  │    │  LLM (chat model │              │
│  │ score Qs)     │    │  via the chat    │              │
│  └───────────────┘    │  provider)       │              │
│         ▲             └──────────────────┘              │
│         │ SystemOne API                                  │
└─────────┼───────────────────────────────────────────────┘
          │
┌─────────┴───────────────────────────────────────────────┐
│  Clef-Flash (9B) via llama.cpp — POST /v1/systemone     │
│  one forward pass → probability per option, no gen      │
└──────────────────────────────────────────────────────────┘
```

Key properties:

- **Bots are clientless** — they speak the RO packet protocol directly (login →
  char → map servers), so each bot is just a socket + a brain. Indistinguishable
  server-side from a real player.
- **Clef does the routine work** — every tick, the bot serializes its state (hp/sp,
  position, nearby players/monsters, inventory, party invites, recent chat) and asks
  ~15 typed questions. The answer arrives as probabilities in one pass (~sub-second
  on a GPU backend).
- **Premade chat lives in Clef's choice space** — "LFP" (looking for party), greetings,
  goal announcements etc. are just options on a `chat_premade` question; the bot emits
  them with zero LLM involvement. Free-form replies go to the chat LLM behind a
  persona system prompt with a governor (cooldown + repeat filter) at the brain.
- **Agents are isolated and scheduled** — each persona knows only what it observed
  (per-agent memory), has a weekly online schedule, and persists across reconnects.
  Friend groups form parties and guilds in-game; coordination happens exclusively
  through in-game channels (party chat, whispers, public chat) — never direct
  state mutation.
- **Everything is traced** — per-agent JSONL history (decides, LLM calls, chat
  heard/sent, actions, script steps, goal reviews) under `--trace-dir`, feeding the
  dashboard history views and future decision improvements.

## Layout

```
src/robots/           the production package
  adapters/           packetdb-backed wire client, chat personas, spawn knowledge
  app/                PlayingClient runtime, brains, scripts, agent host, tracing
  society/            schedules, friend groups, relationships, wants, coordination
  knowledge/          calculators, corpora queries, builds sidecars
  popgen.py           population generator (personas → fixtures → host manifest)
spikes/               the evidence trail (each ends in a `## Verdict:` block)
  001-clef-local/     Clef-Flash behind /v1/systemone + latency bench
  002-rathena-up/     rAthena + MariaDB via nix flake devShell + handshake test
  003-clientless-limbs/  the byte-exact packet table + move/attack/loot/chat/party
  004-brain-loop/     multi-bot Clef tick-loop world
  005/006/            backend benchmarks (GPU, cloud, heavengraph)
dashboard/webapp/     FastAPI + SPA: agents, runs, per-agent history/combat/plans,
                      population generation, live commands (docker-compose on :8401)
scripts/              population_host_runner (scheduled live legs), e2e chain,
                      world recovery, plain-host runner
rathena/              fork of rathena/rathena (submodule, branch bot-infra)
run/
  worlds/             per-world volumes/staging (test-first, e2e, population-live)
  knowledge/          iRO wiki/DB corpora + 13 pre-re build sidecars (binaries
                      gitignored; the build scripts regenerate them)
  reviews/            receipts: benches, migrations, schedules, publication proofs
  plain_host_receipts/  per-leg runtime receipts (steps, decisions, samples)
wiki/                 the project diary + ADRs — read wiki/log.md on resume
```

## Running

The host is NixOS — all dependencies come from nix.

```bash
nix develop -c task check        # the full gate: black/ruff/mypy/xenon/bandit/pytest
nix develop -c task e2e          # the clean-server e2e cycle (compose, ~8.5 min)
nix develop -c task bench        # the decide-backend benchmark rows
```

A live population leg (scheduled agents on the isolated e2e world):

```bash
nix develop -c env PYTHONPATH="$PWD/src" .venv/bin/python -B \
  scripts/population_host_runner.py \
  --manifest .work/runtime/population-live/host-manifest.json \
  --runtime-root .work/runtime/population-live \
  --memory-root .work/runtime/population-live/memory \
  --decision-url http://<clef-host>:8091/v1/systemone \
  --chat-url http://<chat-host>:8092/v1/chat/completions \
  --duration 9000 --worldfeed-port 8402 \
  --heartbeat-min-s 30 --heartbeat-max-s 75 \
  --population-file run/worlds/population-live/population.json \
  --schedule-file run/reviews/population-live-schedule-legN.json \
  --trace-dir .work/runtime/population-live/traces \
  --leg N --out-dir run/plain_host_receipts
```

Schedule windows are `[weekday, start_hour, end_hour]` in the runner's **local time
with Monday=0** (`PersonaClock` uses `datetime.weekday()`).

## Status

Live-proven (population legs 13–25, isolated e2e world, 7 scheduled agents):

- Combat loop: roam → approach → attacks → kills → XP at 7.5× rates
- Economy: kills → drops → pickups → dealer sell chain → zeny
- Social: autonomous party formation (create → invite → accept, persisted in the
  char DB), party chat round-trip, guild create + invite chain
- Chat personas with governor + initiative; connect backoff; full tracing
- World travel via warp routes; build setup (stat allocation from build sidecars)
- Dashboard: tracking, generation, history/combat/plans views, live commands
- Repeated e2e (`task e2e`) on isolated volumes

In progress: full economy closure (sell → knife → equip), WoE arc, sustained
population soak, human-player relationship tracking.

The project diary (what happened, what broke, what was learned) lives in
`wiki/log.md`; the design decisions in `wiki/` ADRs.
