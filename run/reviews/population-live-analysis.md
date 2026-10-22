# Population live run — first sustained-population experiment (2026-10-22)

Branch `feature/population-live-run` (worktree `/tmp/wt-pop`). Raw artifacts:
`.work/population-run/` (git-ignored); commit-able rollups + receipts here.

## What ran

- **Population**: `robots.popgen` seed 3, `--friend-groups 2 --friends-min 2
  --friends-max 3 --solo 1` → **7 personas**: `pop_0003_g00` (NyxSong,
  RinceNyan, zeny_wing), `pop_0003_g01` (PipinWalker, xXLunasongXx,
  PoringMuffin14), solo `pop_0003_s00` (YuffieFy81, pay_fild04 save).
  Accounts 2200000–2200006, chars 300000–300006 (the popgen bands; applied
  on top of the e2e-init default fixture, no band collisions; verified by
  SQL readback: novice start 48/9 points, Basic Skill lv 9, 0 online).
- **World**: the isolated e2e world (project `ro-bots-e2e`, volume
  `ro-bots-e2e-world`, ports 26900/26121/25121, WorldFeed 8402), prepared via
  `scripts/e2e/prepare.sh` + `up.sh` (journal-verified acceptance) + `init.sh`
  once, then the popgen fixture applied directly. Left UP (volume persists).
- **Run**: two legs of `scripts/population_host_runner.py` (new glue: the
  plain-host composition plus passive samples of `brain.decision_count`,
  `agent.online`, and on-disk journal sizes; reads live `host.agents` only,
  cached `last_built_state` for position, no observing reads):
  - leg 1: 3600 s, 14331 host steps, 0 step errors
  - reconnect gap ~16 min (process exit → fresh process, same runtime/memory
    roots)
  - leg 2: 2700 s, 10741 host steps, 0 step errors
- **Backends**: decides = heavengraph `http://192.168.1.156:8091/v1/systemone`
  (read-only shared probes; zero decide-timeout lines in both logs). Chat =
  the canned stub `/tmp/chat_stub.py` on 127.0.0.1:8300 (the local Qwen was
  down at run time; stub pattern per the standing brief).
- **Schedule override (documented)**: popgen's weekly windows were overridden
  to run-spanning windows (the `--playground` semantics, but via explicit
  `--schedule-file` so the per-pair stagger is visible): per roster pair
  (the runtime pairs agents; each pair shares its head's schedule), opens
  staggered +90 s (leg 1) / +75 s (leg 2) to respect the <1 login/5 s churn
  guard, closes ~2–4 min before the runner ends.

## Acceptance (all five verified — population-live-run.json `acceptance`)

1. **Logins + own-position** — PASS. 7/7 agents connected in each leg;
   receipt `pos` observed per agent; ground truth cross-checked in the char
   table: every char's `last_map/x/y` moved from its fixture start cell
   (db-baseline-leg0 → db-final), including **300001 RinceNyan traveling
   cross-map prontera → prt_fild08 (175,358)** in leg 2 (walked the north
   prontera corridor 158,135→158,61→161,361→175,358 across samples). Zero
   reader-death/unknown-packet lines in both logs.
2. **Decisions flow** — PASS. Decides per agent (leg1 max, leg2 max):
   g00m00 5/3, g00m01 2/3, g00m02 5/3, g01m00 6/5, g01m01 6/3, g01m02 6/3,
   s00 5/2 — monotonic growth from the heartbeat decide cadence
   (300–1200 s) + event-driven decides; 0 timeout lines, 0 step errors.
   First decide lands at window open (`agent.start()` seeds Heartbeat(0)).
3. **Schedule adherence** — PASS, both edges, both legs, 7/7 agents:
   `opened_in_window`/`closed_at_window` all true (first-online within 90 s
   of the pair's window open — leg 1 pair 1 connected at t=120.3 vs
   expected 120.0; last-online ≤90 s before close), and NO connection in the
   pre-window samples (leg 1 t=0–90 all offline). Disconnects at window
   close are host-driven (`AgentHost.step` schedule pass), not runner exits.
4. **Reconnect + memory** — PASS. Same runtime/memory roots across the fresh
   process: all 7 journals are byte-exact append-only prefixes of their
   post-restart selves (1→2, 3→10, 1→2, 1→2, 1→2, 1→2, 1→4 lines), journals
   carry the leg-1 `session ended after N ticks as <name>` notes plus leg-2
   received NPC-dialogue pages (g00m01 talked to NPC 110000883 in leg 2);
   chars persisted in the DB with exact positions (`db-between.txt` matches
   each leg-1 receipt's last pos; leg-2 logins resume at those cells).
5. **In-game-only socials** — PASS (conditional branch: no emissions
   occurred). 0 chatlog rows, 0 parties, 0 party memberships for the
   population after ~85 connected-minutes; journals contain only session
   notes and received NPC dialogue (no chat/social kinds). No non-in-game
   channel existed in the composition; the GameAction union admits only
   Say/PartyChat/WhisperTo/InviteToParty as social channels
   (`src/robots/domain/actions.py`). Party-formation behavior under
   schedule-overlap remains unexercised — see below.

## Notes / deviations

- The e2e-init default 2-agent fixture remains in the DB alongside the
  population (harmless; never used by the run manifest).
- The runtime-root (`db/map_cache.dat`, `db/pre-re/mob_db.yml`) was copied
  from the main checkout's `ro-bots-test` runtime assets into
  `.work/population-run/runtime-root` (the e2e chain expects the operator to
  assemble it; `run.sh`'s own check names exactly these two files).
- Roster pairing (playing.build_roster) means the runtime's "groups" are
  pairs over sorted persona ids, not popgen's 3+3 groups; popgen group
  identity is preserved in the population/fixture record.
- Decides are heartbeat-paced (ADR-002), so per-agent counts are ~5 per
  50-min leg, not per-tick; heavengraph aggregate load stayed far below its
  healthy ~1 req/s operating point (7 agents ≈ 0.025 req/s average).

## What's left (not blocking this deliverable)

- Social emissions were never triggered in-window: party invites / chat
  premades need the social objective to fire (heartbeat goal review picked
  town/goal scripts; the solo never crossed the groups' windows in leg
  terms). A follow-up run with overlapping cross-group windows or a longer
  horizon would exercise InviteToParty/PartyChat emissions end-to-end.
- The full `task check` gate was not run in this worktree (scoped lint only:
  black/ruff green on `src tests`; both scripts follow the existing
  scripts/ conventions); the worktree has the vendored rathena submodule +
  config.log copied, so a future gate run is unblocked.
- Multi-hour horizon: this run's connected time is 2×~50 min + 2×~35 min
  window spans inside a >2 h wall-clock experiment; a true overnight
  population run is the natural next scale-up on the same machinery.
