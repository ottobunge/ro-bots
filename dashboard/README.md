# ro-bots dashboard

Rust web dashboard for the ro-bots world — **observer + control plane**
(ADR-007, ADR-008). It is a pure consumer adapter over the `WorldFeed`
contract: no DB, no direct simulation access. While the real Python runtime
feed lands, a seeded `MockWorldFeed` makes everything demoable offline.

## Stack

- **Dioxus LiveView 0.7.10 on Axum 0.8.9** (ADR-007's chosen option; the
  crate is maintained — 0.7.10 released 2026-07, 0.8.0-alpha line active).
  One LiveView route (`/live`) provides the server-rendered auto-updating
  page; everything else is server-rendered HTML + JSON/SSE.
- Tokio 1.53, serde/serde_json for the contract, `rand`/`rand_pcg` for the
  seeded mock.

## Run

```sh
cd dashboard
cargo run --release          # http://127.0.0.1:8400
ROBOTS_SEED=7 cargo run --release   # different initial seed
```

Docker (binds 127.0.0.1:8400 only):

```sh
docker compose -f dashboard/docker-compose.yml up --build
```

## What to open

| URL | What |
|---|---|
| `/` | Roster: agent cards grouped by friend group, online badge from schedule, group attitude label. |
| `/config` | **Configurator** (ADR-008): set seed / friend-group count / solo count / friends-per-group min-max, press **Generate** → POSTs `regenerate_roster`; the mock world regenerates from that seed (exposed in the page header). |
| `/agent/:id` | **Inspector**: persona, current goal/script/plan, personal/group/guild goals, memory view (OptChat `L<level>:<index>` lines), reputation ledger (human, score bar, last reason), characters (name, class path, build), schedule, related events, **edit persona** form, **force action** buttons. |
| `/feed` | Live feed: chat lines styled as MMO chat + world events, operator-forced events tinted/tagged `operator-forced`. |
| `/live` | Dioxus LiveView page: auto-updating roster + event stream over one WebSocket, no client framework. |
| `/api/roster`, `/api/agent/:id` | Snapshot JSON (the WorldFeed query API). |
| `/api/events` | SSE stream of `WorldEvent` JSON. |
| `/commands` | **Write path** (POST): `regenerate_roster`, `edit_persona`, `force_action` (see below). |

## WorldFeed JSON contract

The Python runtime implements this same boundary later. Read path = snapshot
queries + event stream; write path = commands. All types live in the
`world-feed` crate with serde round-trip tests.

### `RosterSnapshot` — `GET /api/roster`

```json
{
  "seed": 42,
  "groups": [
    {"group_id": "Silver Wolves", "attitude": "clique",
     "member_ids": ["mika-01", "doramir-02"], "schedule": [{"day": 1, "start": 18.0, "end": 22.0}]}
  ],
  "agents": [
    {"persona_id": "mika-01", "name": "mika-01", "playstyle": "healer",
     "attitude": "clique", "group_id": "Silver Wolves", "online": true, "chattiness": 0.4}
  ]
}
```

`schedule` windows are weekly `(day 0-6 Mon..Sun, start_hour, end_hour)` and
may wrap midnight (`start > end`).

### `AgentDetail` — `GET /api/agent/:id`

Persona fields + `current_goal` / `current_script` / `current_plan` strings,
`memory_view: [{level, index, summary}]` (OptChat lines, newest last,
`L{level}:{index} {summary}` when rendered), `reputation:
[{human, score ∈ [-1,1], last_reason, last_at}]`, `characters:
[{name, class_path, build_summary, level}]`, `personal_goal` / `group_goal` /
`guild_goal`, `schedule: [ScheduleWindow]`.

### `WorldEvent` — streamed on `/api/events` (SSE) and the LiveView socket

```json
{"ts": 1767588000.0, "kind": "chat",
 "payload": {"line": {"at": 1767588000.0, "channel": "map", "sender": "mika-01", "text": "buffs plz"}},
 "severity": "info", "operator_forced": false}
```

`kind` ∈ `chat | online | offline | goal_change | party_invite | reputation |
wipe | command_ack`; `severity` ∈ `info | notable | alarm`.

### Commands — `POST /commands` (ADR-008)

```json
{"type": "regenerate_roster", "seed": 777, "friend_groups": 3, "solos": 1,
 "friends_per_group_min": 2, "friends_per_group_max": 4}
{"type": "edit_persona", "persona_id": "mika-01",
 "edit": {"name": "mika", "playstyle": "mage", "attitude": "clique",
          "chattiness": 0.5, "schedule": [{"day": 1, "start": 18.0, "end": 22.0}]}}
{"type": "force_action", "persona_id": "mika-01", "action": "chat", "arg": "hello"}
```

`action` ∈ `goal_change | chat | party_invite | disconnect | reconnect`.
Responses are the acknowledged `WorldEvent` (HTTP 200) or a 422 with the
validation error. Every ack is `operator_forced: true` so experiments can
separate organic from injected behavior.

## What is mocked vs real

Everything behind the WorldFeed boundary is currently **mocked**:
`MockWorldFeed` fabricates the whole society from a seed — 3 friend groups
plus 1 solo outsider by default, with ADR-005-style schedules (evening
windows, shared per group, jittered per agent) that tick online/offline on a
virtual clock (1 simulated hour per tick, no wall-clock dependency), chat
lines from chatty online agents, goal changes, party invites, reputation
moves against a fixed set of fake humans, wipes, 5-10-line OptChat-style
memory views, per-human reputation ledgers, and ADR-009-style character
summaries. Same seed → same roster → same event sequence (unit-tested);
commands mutate that deterministic state, nothing else. **Real**: the Axum
server, the LiveView/SSE wiring, the command API shape, and the contract
types themselves. **Not real yet**: no rAthena connection, no Clef decisions,
no actual personalities — the Python runtime will implement `WorldFeed`
(read + `/commands`) and the dashboard code does not change.

## Quality gates

```sh
task dashboard:check   # fmt + clippy pedantic (-D warnings) + test + audit + machete + doc
task dashboard:serve   # cargo run --release
```

`unsafe_code = "deny"`, clippy `pedantic` warnings, and
`unwrap_used/expect_used/panic/indexing_slicing = "deny"` are enforced in
the workspace `Cargo.toml` — the observer loop must not panic.
