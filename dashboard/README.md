# ro-bots dashboard

Rust observer over Python WorldFeed HTTP snapshots and SSE. **Transport integration is not native-game or host-command acceptance.** No DB, game client, or model provider is accessed by this adapter.

## Run with the pinned toolchain

From the repository root:

```sh
nix develop
WORLDFEED_BACKEND=live WORLDFEED_URL=http://127.0.0.1:8400 \
  cargo run --manifest-path dashboard/Cargo.toml --release
# Dashboard binds 127.0.0.1:8401; DASHBOARD_BIND overrides it.

# Offline demo must be an explicit choice:
WORLDFEED_BACKEND=mock ROBOTS_SEED=42 \
  cargo run --manifest-path dashboard/Cargo.toml --release

task -t dashboard/Taskfile.yml dashboard:check
```

Absent `WORLDFEED_BACKEND` means **live**. Unknown modes and invalid URLs fail configuration; connection failure never selects mock. Only mock spawns the synthetic ticker. Every HTML surface visibly labels the backend, and `/api/health` reports identity, available/stale/unavailable status, snapshot age, connection state, errors, and last upstream sequence. The standalone `dashboard/docker-compose.yml` explicitly selects mock; it is not live integration evidence. Docker was not exercised for this change.

## Compatibility, not an invented Python schema

`world-feed/src/wire.rs` deserializes the existing Python API:

- `/feed/roster`: `{agents:[...]}`; no source seed or group schedules.
- `/feed/agent/{id}`: `goal`, `script`, `plan`; memory strings; `agent_score` and `group_score`; character-name strings.
- `/feed/events`: numeric `id` plus `data:{ts,kind,summary,operator_forced}`.

The dashboard snapshot model uses nullable seed, memory indices, character levels, reputation score/timestamp. Missing goals/builds/class paths/reputation reasons are `not supplied`; supplied agent/group scores remain separate. Group associations derive only from supplied roster group IDs; group attitude/schedule and guild/relationship details are not inferred. Raw memory strings are preserved, not parsed into invented hierarchy. Source events remain `kind:source` with `payload.source_kind`, `summary`, and `sequence`; summary text is not interpreted as observed chat/combat/command execution.

## Transport bounds and reconnect

Defaults: 3-second snapshot/command deadlines; 10-second SSE read deadline; 30-second SSE connection deadline; 2-second roster polling; 1-second reconnect delay; 10-second detail-cache TTL. Configuration durations must be nonzero and at most 60 seconds. HTTP bodies cap at 2 MiB; SSE frames at 128 KiB; roster at 4096 agents; cached details at 128; broadcast at 512 events. Redirects/system proxies are disabled. URL credentials, query and fragment are rejected.

Incremental SSE decoding survives LF/CRLF and arbitrary network chunks. Only complete valid numeric-ID events advance the cursor. Reconnect sends `Last-Event-ID`; replayed IDs are deduplicated. Sequence gaps and replayed/lower IDs set independent adapter-lifetime integrity flags, separate from transient transport errors. Successful, empty or comment-only reconnects clear only transport errors. Both integrity warnings remain in `events_error`, alongside any transport error, and keep health stale even while SSE is connected. Only an intentional adapter restart resets these flags together with its cursor; refreshing a snapshot is not history reconciliation. Cached roster is retained on failure but marked stale; before the first successful roster `/api/roster` returns 503. Detail transport failures return 503, distinct from upstream 404.

**Limitations:** Python sequence IDs are process-lifetime, not durable. No server epoch exists: after an upstream restart lower IDs are suppressed; restart/reconfigure the dashboard deliberately to reset its cursor. Evicted history cannot be recovered. Downstream `/api/events` is a bounded broadcast, not durable replay; lagged UI receivers skip events. Static roster/inspector snapshots require reload; `/live` polls roster/health automatically. Quiet streams reconnect on the read deadline and temporarily show stale rather than fabricate activity.

## Commands

Dashboard JSON retains its existing `Command` schema. The live adapter maps roster fields to Python `groups`, `solos`, `friends_min`, `friends_max`, and flattens persona edits. Nonempty schedule-bearing edits are rejected rather than silently dropped. All force actions are rejected because Python currently adds WorldState notes/events, not host effects. `force_schedule` is not exposed by this dashboard contract.

Successful supported POST responses retain the Python source event and explicitly say `execution: "not verified; WorldState only"`. They do not demonstrate AgentHost updates, scheduling, character actions, or gameplay. Rust admission bounds each group/solo count to 4096, friend sizes to 1..16 with min <= max, and the worst-case population `groups * friends_max + solos` to 4096 using checked multiplication/addition. These are resource limits, **not RO party-size rules**; seven-member friend groups remain valid. Live Python separately requires friend sizes >=2. Validation runs before payload construction/network I/O and before mock roster allocation/loops. `MockWorldFeed::with_shape` is now fallible (`Result`), and mock regeneration uses the same guard. **RWF-POP-BOUND-001 remains only partially addressed:** a matching upstream Python resource guard is still a pending prerequisite after the WorldState freeze and independent lifecycle/population reviews. Direct Python callers can bypass Rust admission; no end-to-end resource-bound acceptance is claimed. Commands are not retried automatically because timeout outcomes can be uncertain.

## Evidence and gates

`fixtures/generate.py` creates deterministic snapshots/events using the actual read-only Python serializer with a fixed clock and seed, including memory, characters and separate reputation scores. `fixtures/provenance.json` records source hashes and the offline evidence label. It uses no BotClient/DB/provider.

```sh
nix develop -c uv run python dashboard/fixtures/generate.py
nix develop -c cargo build --manifest-path dashboard/Cargo.toml -p dashboard-app
nix develop -c python dashboard/fixtures/smoke.py
nix develop -c task -t dashboard/Taskfile.yml dashboard:check
```

Rust loopback tests exercise snapshot/detail deserialization, fragmented SSE, reconnect cursor and duplicate suppression, HTTP failures, timeout, command payload translation/rejection, and no-fallback mode selection. The executable smoke runs temporary loopback fixture HTTP and dashboard processes, verifies live/explicit mock labels and stale state after upstream shutdown, then terminates them. **This is fake-HTTP evidence, not native-game acceptance.**

Cargo/rustc/rustfmt/clippy/cargo-audit/cargo-machete come from the root pinned Nix devShell; Taskfile never installs global tools. Axum/Dioxus versions remain those in Cargo.lock. Reqwest is pinned to 0.12.22; request deadlines, per-read deadlines and incremental `Response::chunk` were checked against the author's tagged source before use.
