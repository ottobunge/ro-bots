# Leg 128 verdict — sighting-swing merge validation (2026-11-25, Wed 03:00-04:30 Madrid)

Receipt: `population-receipt-128-1795570819.json` (close-write verified on disk at
04:30 CET while `leg128-runner` was still active — the ad3d2ce0 kill-safety
contract held for the third leg running). Preflight DECIDE-OK **0.47 s
answers=10** at 02:40:04 CET + `:8092` health 200. Launch 02:40:12 CET detached
under `systemd-run --user --unit=leg128-runner`, duration 7,488 s (close 04:30 +
900 margin), RuntimeMaxSec 8,388 = duration + 900. HEAD at launch `cd5e0fca`
(validates the sighting-swing merge: plan-bound receive-side combat leases +
declared-cluster roam bias).

## Runner health

- 22,813 steps, **0 step_errors**. 29/29 online the whole window,
  `offline_agents` empty — cleanest window of the era (leg-127 had one
  end-transient offline).
- Transport rebuilds: all 29 agents carried the one-shot
  `NativeTelemetryUnavailableError` transient, 6-11 attempts each, **none
  exhausted**.
- Decide health (traces, window UTC 01:40-03:30): 3,755 ok / 26 capped =
  **0.7 % capped**, true-success **p50 0.90 s**, p90 3.20 s (leg-127: 3.0 % /
  1.18 s) — healthiest window recorded; the 26 capped attempts are the 25
  tick-failed tracebacks in the runner log (decide-path
  `PlayingBackendError`, agents recovered).

## Bars

| Bar | Result | Verdict |
|---|---|---|
| 1. >= 20/29 attackers with `sighting_swing_minted` taps firing on the roaming 13 | Attackers **21/29** (299 authored -> 187 swings -> 174 damage events -> 3,929 damage); **110 `sighting_swing_minted` taps across 26 agents** incl. 5 on still-zero-attack roamers (g00m02 5, g04m01 5, g03m00 4, g02m02 1, s02 1); **16 `arrival_swing_minted`** across 6 agents (leg-127: 0 — the 223827d2 seam now exercised) | **MET** |
| 2. kills > 25 | **45 kill credits** (leg-127: 25), 153 base / 77 job XP, drops_seen 75, pickups 9/21; picklog M 188 -> **230** (+42 server-side) | **MET** |
| 3. sells continuing vs fleet 2,536 | fleet 2,536 -> **2,710** (+174 = the 11 in-window zenylog S-rows exactly); **10 sellers** (leg-127: 3); picklog S 74 -> 94 | **MET** |
| 4. receipt close-write verified | on disk 04:30 CET, unit still active | **MET** |

All four bars MET — the sighting-swing merge is validated at population scale.

## Participation detail

- New attackers beyond leg-127's 16: the converted roamers include
  pop_0069_g02m00 (32), pop_0069_g03m03 (13), pop_0069_g01m00/g00m00/g00m01 (4
  each), pop_0003_g01m00 (4), pop_0069_g02m01 (3), pop_0069_g04m03/g04m02 (2
  each), pop_0069_g03m01 (1), pop_0069_s03 (6), pop_0003_g00m02 (9).
- 8 zero-attack agents remain (g00m02, g02m02, g03m00, g04m00, g04m01, s00,
  s01, s02): five of them now MINT swings on sighting (the seam fires) but the
  swings refuse (`pending_walk` 144, `cooldown` 85, `target_not_visible` 10,
  `disengage_active` 8 fleet-wide refusals) — minted authority does not
  guarantee a landed swing while the agent is mid-walk.
- Engagement still concentrates: RinceNyan (pop_0003_g00m01) 116 of 299
  attacks; 184 of 347 fleet MonsterSpotted events.

## Sell funnel

- **10 sell conversions in-window** (11 zenylog S-rows, UTC 02:04-02:54 =
  03:04-03:54 CET, amounts 3-80z): RinceNyan +94 (2 rows), NyxSong +28,
  xXDoramrinXx +14, KafraMuffin52 +10, xXLunasongXx +8, TalonWind +6,
  zeny_wing +5, PoringMuffin14 +3, ZenySong +3, VelRin85 +3 — char deltas
  match the rows row-for-row; fleet 2,536 -> 2,710. Best sell window of the
  era (leg-127: +36/3 sellers).
- `sell_contact_authored` 3 (leg-127: 1). Merchant gate telemetry at close:
  `no_stock_below_zeny_floor` 882, `merchant_stock_below_trip_minimum` 312,
  `merchant_trip_retry_cooldown` 62, `counter_not_selected` 43,
  `motion.pending_walk` 41, `contact.received_dealer_adjacency` 39 /
  `contact.counter_turn` 39, `merchant_post_trip_return` 32. One visible miss:
  a sell arm aborted at `dealer_talk_out_of_range` (agent (170,128) vs dealer
  (172,130), chebyshev 2) — adjacency still occasionally off by one.

## pop_0069_s01 ground truth (brief watch item — CORRECTS the roam-reach reading)

- In-window trace: **1 distinct cell** across 5,228 geo-tagged lines — s01
  NEVER left pay_fild04 (163,177), despite 2,513 `move_performed` events and
  5,026 MoveTo actions executed from that cell. DB close position = the same
  cell (163,177), identical to leg-127's close.
- The 0-sightings streak is therefore NOT roam reach and NOT plan-keying (its
  100 plans target the pay_fild04 declared set correctly): **every walk from
  (163,177) fails to land server-side**. Prime suspect: the char is saved on
  an unwalkable cell — rAthena silently rejects every WalkTo whose start cell
  is unwalkable, which reproduces the stuck-forever signature across legs.
- s00 and g04m00 (the other two zero-sighting agents) roamed 281 and 398
  distinct cells respectively — theirs is the ordinary mobless-patch problem,
  not s01's. 28/29 agents roamed 44-684 distinct cells; only s01 is stuck.

## DB readback (docker run sidecar on ro-bots-e2e_default; secret read inside the container only; DB UTC vs runner CET)

- zenylog 47 -> **58** (+11 S-rows in-window; all rows S).
- picklog M 188 -> **230** (+42), P 87 -> **106** (+19), L 128 -> **165**
  (+37), S 74 -> **94** (+20) — every baseline advanced.
- Close positions: 26/29 on prt_fild08 grounds, RinceNyan/prt_in (172,129),
  PoringMuffin14/prt_in (169,129), xXAerofyXx/prt_in (170,128) — the three
  post-sell dealer trips; xXHyupunchXx pay_fild04 (163,177) (s01, stuck cell).
- Three chars remain at base 11 (RinceNyan, PipinWalker, xXLunasongXx); the
  153 base XP did not produce a new level this window.

## Decisions taken

- `seed-zeny.json` advanced to the post-window fleet **2,710** (zeny CHANGED):
  10 personas moved, 19 verified unchanged against the DB, delta reconciles
  exactly against the 11 zenylog rows.
- Receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit,
  explicit paths, pushed.

## Named next signature

**s01's walk-landing defect (primary).** The sighting-swing seam now mints
authorities fleet-wide (110 sighting mints) and participation holds above the
bar (21/29), but pop_0069_s01 sits at pay_fild04 (163,177) executing thousands
of MoveTos that never land server-side — one cell across the whole window,
across legs. Diagnose the saved-cell state: confirm (163,177) walkability in
the pay_fild04 gat, and add stuck-detection (N consecutive `move_performed`
with zero tracked-position change -> transport rebuild or position reset)
before it burns another leg. Secondary: minted-but-refused swings on the five
roaming minters (pending_walk/cooldown dominate) — the mint should defer
until walk-release instead of refusing; and the dealer-adjacency off-by-one
(`dealer_talk_out_of_range` chebyshev 2).
