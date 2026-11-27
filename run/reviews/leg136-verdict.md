# Leg-136 verdict — Fri 2026-11-27, window 20:00-21:30 CET (schedule [[4,20.0,21.5]] all 29)

Base: main `1037bb94` (leg-135 census fix — persistent patrol waypoint — merged before launch
and therefore validated live; local checkout had moved `a5b1cf4b` → `1037bb94` while the
shepherd slept). Schedule staged `a5b1cf4b`. Shepherd: T3 subagent, leg-136 brief.
Receipt: `run/plain_host_receipts/population-receipt-136-1795804324.json` (6.6 MB, written 21:28).

## Preflight + launch

- PREFLIGHT PASS 19:32 CET: `date '+%a'` = vie (weekday 4 = schedule index 4); decide probe
  **DECIDE-OK 0.55 s warm, answers=10** on `http://192.168.1.156:8091/v1/systemone`;
  :8092 `/health` 200. No stale runner, worldfeed 8402 free.
- Pre-window DB double-read: fleet **3,973z** — all 29 persona zeny per-char identical to
  seed-zeny.json (rebased `46dbd4ec`); only extras are the 0z FX fixture chars.
- Launch **19:32:04 CET** via the proven inline `systemd-run --user --unit=leg136-runner
  --property=RuntimeMaxSec=7200 bash -c ...` form. Log within 60 s: all 29 personas rostered,
  `CLOCK: (4, 19.53)`, `SCHED:` windows `((4, 20.0, 21.5),)` × 15 playing groups, configured True.
- **Launch-timing lesson:** the RUNBOOK band was 19:40-19:55; firing at 19:32:04 (right at the
  wake) means the fixed `--duration 6900` ended **21:27:04**, ~3 min before the nominal 21:30
  close — the final ~3 min of the window ran without agent sessions. For a 20.0-21.5 window the
  earliest clean launch with this duration is ≈19:40 (launch + 6900 s ≥ close + drain). Leg-135's
  08:41 launch covered its window because it also started 18.5 min early but 6900 s reached past
  its close. No data was contaminated (all DB window filters are timestamp-based); coverage was
  87 of 90 min.

## Mid-window states

- 20:08 (+8 min past open): **29/29 online, 457 decides**; transport_down 21 building toward the
  login-burst pattern; 0 login failures.
- 20:18: 29/29, 1,091 decides, transport_down 28, 6 pickups dispatched; mid-window DB readback
  fleet already **4,041z (+68)** — sell verdict landing 70+ min early.
- 21:04: 28/29 (single-sample transient), 3,127 decides, transport_down **29 (frozen since the
  burst)**, 14 pickups; fleet **4,592z (+619)**, 10 net-positive, 0 net-negative.

## Close

- Window held 29/29 online; final sample (t=6900.2) reads **online 29/29**. Receipt written
  **21:28 while `leg136-runner` was still active**; unit drained itself after
  `DONE: steps 23684, errors 0` — kill-safety law held, **close-write 13th consecutive**.
- Receipt figure: **steps 23,684, step_errors 0**, offline_agents [], samples 229. (Tonight the
  receipt `steps` equals the DONE line — the post-close drain advanced the runner step counter by
  0; the agent `ticks` series still shows the drain: 47,251 window ticks → 67,725 final.)
- Close DB double-read: fleet **4,618z**; zenylog window rows (UTC-stamped: log hours 19+20;
  anchor proof — leg-135's CET 09:02-10:27 sells sit at log hours 08-09): **S 18**;
  picklog **M 39 / P 29 / L 24 / S 23**.

## Decide health (error-field split)

4,427 windowed `decide_response` rows across all 29 agents (111-388 per agent). Capped (rows
carrying `error`): **41 = 0.93%** (`PlayingBackendError`). TRUE success p50 **1.05 s**
(p95 9.47 s, max 14.33 s). Backend exonerated for every soft number in this window.

## Transport

TRANSPORT DOWN: 29 lines, distribution exactly 1 per agent in the login burst — the documented
shared transient. Every agent rebuilt (transport_recovery attempts 8-14, **exhausted: false**
fleet-wide); no mid-window repeats after ~20:18.

## Bars

| # | Bar | Result | Verdict |
| --- | --- | --- | --- |
| 1 | BOTH-ARM: attackers ≥15/29 AND sellers ≥10/29 | attackers **17/29**, sellers **12/29** | **PASS** (leg-135: 12/11) |
| 2 | kills ≥30 (recovery floor) | **41** kill_credits, 14 agents credited (top pop_0069_g02m02 7) | **PASS** (+22 vs leg-135's 19) |
| 3 | fleet zeny net-positive vs 3,973 | **4,618 (+645)**, 12 sellers, S-sum 645 = delta **exact reconciliation** | **PASS** |
| 4 | movement census routing recorded | MoveTo **26,777/27,877 = 96.1%**; purpose split roam 26,570 (99.2%) / approach 117 / loot 23 / merchant 16; census-fix class split below | **PASS** (recorded) |
| 5 | receipt close-write 13th consecutive | landed 21:28 with unit active | **PASS** |

**Overall: 5/5 bars PASS.** First 5/5 of the recovery arc; BOTH-ARM and the kill floor both
recovered (attackers 12→17, sellers 11→12, kills 19→41), fleet zeny +645 in 87 min (leg-135:
+154 in 90).

## Movement census (the named-next readout — windowed 27,877 `action_executed` rows)

- Kinds: MoveTo 26,777 (96.1% vs leg-135's 97.8%); GuildInvite 341; Attack 299; Say 220; Loot 88;
  Rest 38; InviteToParty 28; PartyChat 25; TalkToNpc 16; NpcShopSellOpen 16; FoundGuild 15;
  NpcShopSell 9; WhisperTo 5.
- **MoveTo purpose split** (next non-MoveTo action of the same agent within 30 s classifies the
  walk; unpaired = roam): **roam 26,570 = 99.2% of MoveTo**, approach 117, loot 23, merchant 16,
  other 51. Roam still owns the walk budget — but it is no longer blind: **17/29 agents showed
  nearby_n > 0 at some sample** (leg-135: fleet-wide 0) and all 29 agents displaced.
- **Census-fix class split (1037bb94, persistent patrol waypoint):** consecutive same-target
  MoveTos (held waypoint) **22,575 = 84.3%**; retargeted 4,202 (15.7%) — the hold is visible
  live in its own class, and the synthetic-replay claim (abandoned-before-next → 0) is
  consistent with the live retarget rate being dominated by arrival/displacement/goal-flip
  retargets.
- Attack budget: 379 attacks authored → 299 executed (245 swings, 4,969 damage). Gate census:
  `pending_walk` **1,427**, `cooldown` 983, `disengage_active` 361, `target_not_visible` 104,
  `out_of_melee_range` 9, `dead` 4. Zero-attack cohort **12** agents (leg-135: 17).
- Sell funnel: TalkToNpc 16 → NpcShopSellOpen 16 → NpcShopSell 9 executed; 12 sellers in the DB
  (top SoraSama22 2 sells / 509z). Receipt 30 s samples caught npc_stage on only 2 agents and
  shop_offer on 0 — shops open for seconds between samples; the DB rows are the ground truth.
- Chat WATCH: 10 agents exceeded 10 chat actions (250 chat actions total vs leg-135's 160 by 3
  agents) — the chat share rose ~57% while chat agents heavily overlap the 12-agent zero-attack
  cohort. Not a bar; flagged for the next census pass.

## Named-next signature

**pending_walk owns the attack loss.** 1,427 `pending_walk` gates vs 379 authored attacks: an
authored attack waits for an approach walk that the roam waypoint hold keeps re-authoring over —
approach walks are 0.4% of the MoveTo budget while roam is 99.2%. Next readout: per-agent
pending_walk counts against each agent's roam-waypoint cadence to decide whether attack
authoring must PREEMPT the roam hold (displace-on-attack) or the approach walk needs budget
priority. Do NOT open another chat slice before routing this. Purchaser-pooling stays flagged
for Otto (below).

## Buy-leg watch

PoringMuffin14 970 → **1,007z** (+37, 3 sells) — still **243z short** of the 1,250z knife (1204).
Accumulation cadence unchanged; purchaser-pooling design stays flagged for Otto.

## Artifacts

- Receipt: `run/plain_host_receipts/population-receipt-136-1795804324.json`
- Census: this verdict's numbers computed over `.work/runtime/population-live/traces/*.jsonl`
  windowed 2026-11-27T19:00:00 → 20:31:00 UTC (script: census pass in shepherd transcript;
  window filter derived from schedule Madrid hours + CET offset per the trace law)
- Runner log: `/tmp/population_leg136.log` (DONE 23,684 steps, 0 errors)
- Pre/close DB reads: `/tmp/zeny-pre-136.txt`, `/tmp/zeny-mid-136.txt`, `/tmp/zeny-mid2-136.txt`,
  `/tmp/close136.txt` (uncommitted, /tmp only — no secrets)
