# Leg 126 verdict — pop_0069 plan-target validation (2026-11-24, Tue 20:00-21:30 Madrid)

Receipt: `population-receipt-126-1795545427.json` (close-write verified on disk at
21:30:38 CET while `leg126-runner` was still active — the ad3d2ce0 kill-safety
contract held). Launch 19:36:59 CET after preflight DECIDE-OK 0.57s / :8092 health 200.
duration 7,681s (close 21:30 + 900 margin), RuntimeMaxSec 8,581; unit released itself
22:00, NRestarts 0. HEAD at launch `d6d4fdb7` (validates `8a8c5853`).

## Runner health

- **29/29 online the entire window** (`offline_agents: []`), 15,744 steps, **0 step_errors**.
- Transport rebuilds: 22 agents attempted (3-4 attempts each), **none exhausted** — the
  same one-shot `NativeTelemetryUnavailableError` keepalive transient shape as leg-125's
  19, all recovered in-window.
- Decide health (traces, window UTC 18:37-20:30): 9,271 `decide_response` rows,
  **28.5 % capped**, true-success **p50 14.03 s** (leg-125: 26.7 % / 13.97 s) — the same
  load-dependent saturation band, capped share slightly deeper.

## Bars

| Bar | Result | Verdict |
|---|---|---|
| 1. >= 20/29 attackers, pop_0069 zero-authored set collapsing | **6/29** attackers (87 authored, 61 swings, 950 damage); pop_0069 zero-authored **20/25** (leg-125: 17) | **NOT MET** (leg-125: 10/29) |
| 2. kills > 23 AND pickup_success > 0 | kills **15** (< 23) — NOT MET; pickup_success **4/6** > 0 — the leg-125 pickup regression RECOVERED (0/2 -> 4/6) | **SPLIT** |
| 3. sells continuing vs fleet 2,457 | fleet 2,457 -> **2,500** (+43; 3 in-window zenylog S-rows) | **MET** |
| 4. receipt close-write verified | on disk 21:30:38, unit still active | **MET** |

## The 8a8c5853 plan-target fix — verdict

**The fix did its job at the plan level; participation did not follow.**

- 22 of the 23 zero-authored agents now carry heartbeat plans targeting the DECLARED
  prt_fild08 species `[Lunatic, Drops, Pupa, Poring]` (2-36 plan_authored rows each,
  per-agent traces). The leg-125 "plans never target reachable species" defect is CLOSED.
- The one remaining target-quality exception is **pop_0069_s01** (xXHyupunchXx): 61 plans
  targeting `[Deviling, Angeling, Ghostring, Poporing, Marin, Mastering...]` — the
  pay_fild04 rare set — while standing on prt_fild08; it authored **1,855 MoveTos**
  chasing undeclared species. Cross-map persona goal keys, exactly the shape the wiki
  entry for 8a8c5853 predicted.
- Participation regressed instead: the zero-authored agents are **CHAT-BOUND**. In-window
  `action_executed`: Say 15-261 per agent vs MoveTo 0-11 and Attack 0 — g02m00
  245 Say / 1 MoveTo / 0 Attack; s00 208 / 1 / 0; g03m00 248 / 0 / 0; s02 235 / 0 / 0.
  Their 359 decides (106 capped) produced chat, not farm-script steps. This is the
  independent scheduling/chat signature the 8a8c5853 wiki entry already flagged
  (pop_0069: 6,566 ChatHeard vs 40 MonsterSpotted) — it is now the dominant limiter.
- Funnel for the 6 engaged agents: 87 authored -> 61 swings -> 58 damage events ->
  950 damage -> **15 kill credits** -> 76 base / 36 job XP; drops_seen 6, pickup
  attempts 6, success 4. attack_refusals fleet-wide are small (pending_walk 24,
  cooldown 9, target_not_visible 2, disengage_active 2, dead 1) — refusals are no
  longer the story; authorship is.

## Sell conversions (3, in-window)

- PipinWalker (pop_0003_g01m00) +35z (UTC 19:47), RinceNyan (pop_0003_g00m01) +5z
  (UTC 20:25), SoraSama22 (pop_0069_g01m00) +3z (UTC 19:46) — char deltas match the
  zenylog rows row-for-row; fleet 2,457 -> 2,500.
- `sell_contact_authored` log taps 0 — the pump-authored contact path never fired; the
  three sells came through decided/script contacts. Merchant gate telemetry shows the
  admission correctly refusing the farm-less fleet: no_stock_below_zeny_floor 703,
  merchant_stock_below_trip_minimum 280, counter_not_selected 121,
  map_not_on_merchant_route 64, pending_walk 60.

## DB readback (docker run sidecar on ro-bots-e2e_default; secret inside container only)

- zenylog 39 -> **42** (+3 S-rows, all in-window UTC 19:46-20:25).
- picklog M 155 -> **167** (+12), P 67 -> **73** (+6), L 100 -> **106** (+6), S 63 -> **66** (+3).
- Close positions: 26/29 on prt_fild08 grounds, PipinWalker in prontera (157,58),
  RinceNyan on prt_fild06 (32,197), xXHyupunchXx still pay_fild04 (163,177).

## Decisions taken

- `seed-zeny.json` advanced to the post-window fleet 2,500 (zeny CHANGED): exactly three
  personas moved (pop_0003_g00m01 222->227, pop_0003_g01m00 168->203, pop_0069_g01m00
  16->19); all other 26 personas verified unchanged against the DB.
- Receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit, explicit paths.

## Named next signature

**Chat-dominated decide budget (primary).** Plan quality is fixed; the participation
limiter is that pop_0069's decide cadence is spent on chat (Say storms at 15-261/window
against 2-36 heartbeat plans and 0 attacks). Lever: cap/gate the chat governor under an
active farm plan (chat only after the script stepped, or a per-window Say budget), then
re-measure attacker participation — the target species are declared, walkable and
reachable on prt_fild08, so authorship should follow the freed decide budget.
Secondary: pop_0069_s01's cross-map plan targets (pay_fild04 rare set on prt_fild08) —
retarget its goal keys or exclude non-declared species for its map.
