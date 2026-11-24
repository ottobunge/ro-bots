# Leg-124 verdict — socializer field gate + receipt kill-safety + expless retarget

- **Leg:** 124, staged commit `2fa6a957` (ad3d2ce0 merge under it)
- **Window:** Tue 2026-11-24 09:00-10:30 Madrid (schedule `[[1, 9.0, 10.5]]`, 29 personas)
- **Launch:** 08:42:45 CET detached via `systemd-run --user --unit=leg124-runner`, duration 8,235 s
  (window close 10:30 + 1,800 s slack), **RuntimeMaxSec 9,135 s = duration + 900** (CARRY LAW)
- **Receipt:** `run/plain_host_receipts/population-receipt-124-1795506172.json` (4.1 MB)
- **Preflight:** DECIDE-OK 0.46 s answers=10 warm; :8092 health 200; :8091 health 200
- **Runner health:** 29/29 online the whole window, 13,569 steps, **0 step_errors**, offline_agents [],
  transport_recovery attempts on 3 agents (2-4 retries, none exhausted)

## Bars

### Bar 1 — >=20/29 agents with >=1 authored attack (goal persistence vs chat re-claim): **NOT MET — 8/29**

Attackers (attacks_authored): pop_0003_g01m02 64, g00m00 41, g01m01 39, pop_0069_s00 37,
g01m00 37, g00m01 33, g00m02 9, pop_0069_g00m02 3 — all six group-0003 members attacked,
only 2 of the 22 pop_0069 agents did.

Fleet attack totals: 263 authored / 128 swings sent / 2,267 damage / **16 kill credits** /
108 base + 38 job XP / 12 drops seen / 3 pickups.

What worked: the socializer field gate ROUTED — 2,090 `goal_field_routed` taps, and the DB
close positions show 21+ agents ON field grounds (prt_fild08 spawn cluster 165-188 x 354-375,
one odyssey walker in pay_fild04). Chat did NOT re-claim field goals this window
(`goal_persistence_expired` only 5, no re-claim storm like leg-123's 11).

What did not: attack authorship did not spread. The dominant gate refusal is
`pending_walk` 373 (vs 46 disengage_active, 33 cooldown) — agents arrive near targets
mid-walk and defer the swing to a tick that mostly does not come for the non-attacking 21.
The walk→swing seam is the next signature (below).

### Bar 2 — receipt WRITTEN AT CLOSE before envelope drain (ad3d2ce0 kill-safety): **MET, PROVEN**

`population-receipt-124-1795506172.json` mtime **10:30** — written exactly at window close
while the unit was STILL ACTIVE (duration envelope ran to 11:00, RuntimeMaxSec to 11:15).
Close-write preceded drain; zero receipt loss (the 3 RuntimeMaxSec losses of the leg-121-123
era are eliminated by design, now live-proven).

### Bar 3 — expless retarget firing (farm_retarget taps; drops > 0): **NOT EXERCISED**

`farm_retarget` taps: 0. `drops_seen` 12 > 0 (loot pipeline live), but no agent farmed into
an expless-species target this window, so the retarget trigger never arose. Taps-at-zero =
never-exercised, never a pass; the mechanism remains unvalidated live.

### Bar 4 — sell conversions continuing: **MET — 3 in-window conversions**

zenylog rows 34-36, all inside the window (DB UTC): PoringMuffin14 **+630z** @ 09:20:33,
YuffieFy81 +4z @ 08:23:47, PipinWalker +4z @ 09:25:36 — type S. Fleet zeny
**1,798 -> 2,436 (+638 = exactly the three sales' sum)**. Both PoringMuffin14 and YuffieFy81
closed standing INSIDE prt_in at the dealer. No purchases this window (all new rows are S).
`sell_contact_authored` tap stayed 0 in the runner log while the conversions went through the
script/pump path — the receipt-side gate sample slot (`merchant_contact_gates`) is null.

## Decide health (traces, window-filtered UTC 07:42:50-09:31:00)

9,339 decide_response rows; **22.1 % capped** (PlayingBackendError), true-success **p50 13.78 s**
(leg-123: 16.4 % / 13.01 s) — same load-dependent saturation band, no regression.

## DB readback (docker run sidecar on ro-bots-e2e_default; secret read inside container only)

- zenylog 36 rows (baseline 33): +3, all this window
- picklog M135 / P65 / L67 / S59 (baselines M120+ / P57+ / L27 / S44+ — all up)
- Close positions: 25 field agents clustered on prt_fild08 grounds, 2 in prt_in (dealer),
  2 prontera, 1 pay_fild04 odyssey

## Decisions taken

- seed-zeny.json refreshed to the post-leg-124 fleet baseline (2,436) — zeny CHANGED
- receipt, verdict, wiki/log.md entry, seed-zeny.json committed in ONE commit, explicit paths

## Named next signature

**The walk->swing seam for the non-attacking 21.** Field routing converges (2,090 routings,
fleet ON the mob grounds) but only the group-0003 cluster converts adjacency into authored
attacks; 373 `pending_walk` refusals say arrivals land mid-walk and the deferred swing is
rarely re-minted. Lever: when a pending walk arrives with a live attack candidate, author the
swing in the same tick budget (arrival-release -> immediate swing), then re-measure the
attackers count. Secondary: give pop_0069 agents the same farm-plan target quality as the
group-0003 cluster (8/29 attackers are 6/6 group-0003 + only 2/22 pop_0069 — the split is
group-shaped, not distance-shaped).
