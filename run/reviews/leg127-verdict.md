# Leg 127 verdict — chat-budget gate validation (2026-11-24, Tue 22:30-23:54 Madrid)

Receipt: `population-receipt-127-1795555351.json` (close-write verified on disk at
23:54:37 CET while `leg127-runner` was still active — the ad3d2ce0 kill-safety
contract held). Preflight DECIDE-OK 0.49 s answers=10 at 22:22 (the :8092 curl was
skipped, time-pressed per the brief; the window itself exercised chat heavily, so
the chat backend was live). Launch 22:22:25 CET detached under
`systemd-run --user --unit=leg127-runner`, duration 6,155 s (close 23:50 + 900
margin), RuntimeMaxSec 7,055 = duration + 900. HEAD at launch `0981f73d`
(validates the chat-budget gate merge `a9f0f304`: per-agent cap of 3 chat
decisions + 3 messages per rolling 120 s while an active unspent farm plan is
live; re-opens on plan completion/drop).

## Runner health

- 18,944 steps, **0 step_errors**. 29/29 online through the window except one
  end-transient: pop_0003_g00m02 (mid-window drop at t=3232.6 recovered, offline
  again at the close sample t=5488.9; 5 rebuild attempts, none exhausted).
- Transport rebuilds: all 29 agents carried the one-shot
  `NativeTelemetryUnavailableError` transient (5-6 attempts each, none exhausted) —
  the same shape as legs 125/126.
- Decide health (traces, window UTC 21:22-22:54): 3,443 ok / 107 capped =
  **3.0 % capped**, true-success **p50 1.18 s**, p90 8.03 s (leg-126: 28.5 % /
  14.03 s) — the healthiest window of the saturation era. Consistent with the chat
  gate removing per-tick chat generation from the decide path, and with the known
  window-variable backend load; do not read it as a server-side cure.

## Bars

| Bar | Result | Verdict |
|---|---|---|
| 1. >= 20/29 attackers, Say collapse on plan-carrying agents, chat_budget_gated taps | Attackers **16/29** (173 authored, 120 swings, 114 damage events, 2,315 damage). Say storms **COLLAPSED**: fleet max 13/agent (leg-126: 15-261; worst g02m00 245 -> 5), **4,342 `chat_budget_gated` taps across all 29 agents** (84-203 each) | **SPLIT** — gate mechanism MET (collapse + taps everywhere), participation bar NOT MET (6 -> 16, < 20) |
| 2. kills > 15 | **25 kill credits**, 75 base / 42 job XP, drops_seen 31, pickups 11/15 | **MET** (leg-126: 15, leg-125: 23) |
| 3. sells continuing vs fleet 2,500 | fleet 2,500 -> **2,536** (+36 = the 5 in-window zenylog S-rows exactly); 3 sellers; picklog S 66 -> 74 | **MET** |
| 4. receipt close-write verified | on disk 23:54:37 CET, unit still active | **MET** |

## The chat-budget gate (a9f0f304) — verdict: the gate did its job

- **Say authorship collapsed fleet-wide**: max 13 Say/agent in-window (pop_0003_s00)
  vs leg-126's 15-261 band. The gate fired continuously — every agent logged
  84-203 `chat_budget_gated` taps (4,342 total).
- **The freed decide budget went to movement**: the pop_0069 agents authored
  1,991-2,288 MoveTos each (leg-126: 0-11); pop_0003_g00m01 1,433 MoveTos + 65
  attacks. Chat no longer consumes the budget; walking does.
- **Participation tripled but missed the bar**: 16/29 attackers (leg-126: 6,
  leg-125: 10). The 13 zero-attack agents all roamed hard and 12 of 13 saw mobs
  (1-7 sightings each) but authored 0 swings. Only pop_0069_s01 saw nothing.
- Engagement remains concentrated: pop_0003_g00m01 (RinceNyan) authored 85 of the
  173 attacks (49 %) and spotted 113 of the 210 fleet MonsterSpotted events.
- `arrival_swing_minted` 0 taps — the 223827d2 arrival-swing seam was never
  exercised this window (taps-at-zero = never-exercised, not a pass).
- Attack refusals fleet-wide: pending_walk 70, cooldown 64, target_not_visible 5,
  disengage_active 1, out_of_melee_range 1.

## Sell funnel

- **3 sell conversions in-window** (zenylog rows 43-47, UTC 21:35-22:40):
  RinceNyan +27z (3 rows), ZenySong +6z, PoringMuffin14 +3z — char deltas match
  the rows row-for-row; fleet 2,500 -> 2,536.
- `sell_contact_authored` 1 (23:30 CET) — the pump-authored contact path fired for
  the first time (leg-126: 0); the other two sellers came through decided/script
  contacts. No counter-parking signature: counter_not_selected only 12 (leg-126
  era parked whole rings).
- Merchant gate telemetry shows admission correctly refusing a mostly-broke fleet:
  no_stock_below_zeny_floor 921, merchant_stock_below_trip_minimum 333,
  merchant_trip_retry_cooldown 183, approach.pickup_required 21.

## pop_0069_s01 ground truth (brief watch item — CORRECTS leg-126)

- DB: `xXHyupunchXx` closed on **pay_fild04 (163,177)** = receipt close pos =
  trace position. Its 95 plans target the pay_fild04 declared set
  (Deviling/Angeling/Ghostring/Poporing/Marin/Mastering/Drops/Poring) —
  **MAP-CONSISTENT**. Leg-126's "cross-map plan targets while standing on
  prt_fild08" reading is corrected: the plan keys the map the char is actually on.
- The real deficit: 2,288 MoveTos, **0 MonsterSpotted** — it roamed a mobless
  pay_fild04 patch the whole window. The question is roam reach/coverage on
  pay_fild04 (spawn scatter, roam radius), not plan-keying.

## DB readback (docker run sidecar on ro-bots-e2e_default; secret read inside the container only; DB UTC converted vs runner CET)

- zenylog 42 -> **47** (+5 S-rows in-window UTC 21:35-22:40; all 47 rows are S).
- picklog M 167 -> **188** (+21), P 73 -> **87** (+14), L 106 -> **128** (+22),
  S 66 -> **74** (+8) — every baseline advanced.
- Close positions: 26/29 on prt_fild08 grounds (scattered x 163-261, y 320-371),
  xXHyubladeXx prontera (148,131), RinceNyan prt_fild06 (42,229),
  xXHyupunchXx pay_fild04 (163,177).
- Three chars closed at base_level 11 (PipinWalker, RinceNyan, xXLunasongXx) —
  the 25-kill XP visible on chars for the first time since the 7.5x rates.

## Decisions taken

- `seed-zeny.json` advanced to the post-window fleet **2,536** (zeny CHANGED):
  exactly three personas moved (pop_0003_g00m01 227->254, pop_0069_g03m03 10->16,
  pop_0003_g01m02 764->767); the other 26 verified unchanged against the DB.
- Receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit,
  explicit paths, pushed.

## Named next signature

**Sighting->swing conversion for the roaming 13 (primary).** The chat gate fixed
the budget (Say collapsed, taps everywhere) and participation tripled (6->16), but
the 13 zero-attack agents now spend that budget roaming (~2,000-2,300 MoveTos
each) through mob-visible territory without ever swinging: sightings are sparse
and fleeting (1-7 each), refusals are pending_walk 70 + cooldown 64, and the
arrival-swing seam logged 0 mints — a sighting or a walk release is not converted
into a swing within its own window. Lever: author the swing in the same budget as
the sighting (spot-driven interrupt in the script step, or extend the
arrival-swing handoff to roam-walk release events), then re-measure the 20/29 bar.
Secondary: pop_0069_s01's pay_fild04 roam has zero mob visibility (0 sightings /
2,288 MoveTos) — extend its roam reach toward pay_fild04's declared spawn cells or
route it back to prt_fild08 grounds; plan-keying itself is correct.
