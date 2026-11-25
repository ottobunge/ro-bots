# leg-129 verdict — walk-landing recovery validated, escape bar MET with a named residual

Leg 129 ran Wed 2026-11-25 09:00–10:30 Madrid (schedule `[[2,9.0,10.5]]`, 29 personas) on
main `206fa16c` (carries db33d1a2, the walk-landing recovery merge). Shepherd launch
08:41:33 via `systemd-run --user --unit=leg129-runner` (RuntimeMaxSec 8340, duration
7440 = close+900), preflight green (DECIDE-OK 0.49s answers=10, chat 200, all four e2e
containers up, seed rebase 29/29 exact vs `seed-zeny.json`, fleet 2710).

**Operator reset applied pre-launch (coordinator-authorized):** `char` 300119
xXHyupunchXx last position pay_fild04 (163,177) → (20,165), via the docker-run client
sidecar with a mounted SQL file (backtick-quoted `char`, secret expanded inside the
container, verify SELECT read back `pay_fild04 20 165`). Note for future sidecar users:
the `< /q.sql` redirect must sit INSIDE the `sh -c` string; outside it, the host shell
resolves the path and the call fails with "/reset.sql: No such file or directory" — the
mount itself was never the problem.

Receipt: `run/plain_host_receipts/population-receipt-129-1795592488.json` — close-write
verified ON DISK at 10:31 with the
unit still active (kill-safe shape), and the runner exited clean:
`DONE: steps 23699, errors 0` at 10:50.

## Bars

1. **s01 xXHyupunchXx ESCAPES (163,177) — MET, with the residual named.** Window-filtered
   trace geo-rows: 60 distinct received cells, first (`pay_fild04`,20,165) — it logged in
   at the reset cell and roamed, authoring 2,378 MoveTos, 7 attacks, 1 kill (+2 exp), 1
   pickup, 14 sightings. Then: monster kill 09:04:45 local, rest-recovered, SELF-DEATH
   09:09:59 (target 2210019 = own aid) → rAthena respawn to its SAVEPOINT — which IS the
   unwalkable (163,177) (popgen seeded the savepoint there; the reset deliberately moved
   only last_map/x/y) — and the agent spent the remaining ~80 min re-trapped: the cell
   sits in a SEALED unwalkable pocket (GAT-verified in the db33d1a2 lane: no walkable
   cell within radius 2 or 12; nearest is (182,158), Chebyshev 19), so both recovery
   stages find no candidate and exhaust; moves from an unwalkable own-cell are rejected
   server-side and no runtime path can extract the agent (7 detected/7 escalated cycles,
   no landing). Logout row therefore reads (163,177) again — a respawn re-trap, not a
   recovery failure and not a DB-reset miss.
2. **Attackers hold >= 21/29 — MET, 26/29** (leg-128: 21/29). Zero-authored collapsed to
   3 (`pop_0069_g00m03`, `pop_0069_g02m01`, `pop_0069_s03`), all three roamers with
   500-770 distinct cells but 1-4 sightings — mobless-patch coverage, not conversion. The
   deferred-mint change (441bd90b line of work, merged db33d1a2) did NOT regress
   participation.
3. **Kills vs 45, zeny vs 2710 — economy GREW, kills dipped.** kill_credits 39 (leg-128:
   45, −13%) — per-attacker rate fell 2.14 → 1.5 as participation widened; picklog M
   rows in-window +39 correlate with kill_credits exactly. Fleet zeny 2710 → **2789
   (+79, TEN distinct sellers)** — the strongest sell window of the era (leg-128: 3
   sellers +36); zenylog 11 `S` rows in-window sum to exactly +79 (no purchase offsets —
   per-agent deltas sum to the same figure). Picklog in-window: M+39 / P+23 / L+18 /
   S+16 (close totals M269 / P129 / L183 / S110, zenylog S 58 → 69).
   **Brief-baseline correction (the file/current readback is the authority):** the brief
   quoted leg-128 picklog baselines M230/P73/L106/S66; the staged pre-launch readback was
   M230/P106/L165/S94 — P/L/S in the brief were pre-leg-128 figures. M matched; deltas
   here are computed from the CURRENT pre-window readback.
4. **stuck_cell taps behave — MET.** Runner log: 29 `stuck_cell_detected`, 13
   `stuck_cell_escalated`, zero unbounded churn (max per agent: s01's 7+7 cycles; all
   other detections 1-3 on walkable cells). Receipt move-gate tail: stuck_cell_reset 10 /
   stuck_cell_exhausted 16 (rolling-deque ranking, not window totals). Every s01
   detection names `cell=(163, 177) own_walkable=False` — the grid confirms the cell is
   unwalkable and the detection is honest. Recoveries are bounded by design (2 direct
   attempts per received cell → exhausted → fail_patrol → replan).
5. **Receipt close-write verified — MET** (above).

## Health

steps 23,699 / 0 step_errors; decide regime: 3,900 answered / 23 capped = **0.6%
capped, success p50 0.84–1.18 s per agent (fleet ~0.96 s), p90 1.7–4.3 s** — the
healthiest regime of the saturation era (leg-128: 0.7% / 0.90 s). TRANSPORT DOWN: 29
lines = exactly one per agent (the shared open transient), 0 exhausted, all recovered
(final sample 28/29; `pop_0069_g02m02` the end-transient offline — same shape as
leg-128's). Sell funnel: `sell_contact_authored` 10 firings / 8 distinct pump-contact
bots beside 10 realized sellers — the healthy two-arm shape (aero_song, ZenySong sold
via decide-authored talks; sora_sama, rince_ko authored holds that did not complete;
rince_ko closed dealer-adjacent at prt_in). Merchant admissions named their conjuncts
(no_stock_below_zeny_floor, merchant_stock_below_trip_minimum, trip_retry_cooldown).

## Named next signature

The popgen savepoint of pop_0069_s01 sits ON the unwalkable (163,177): every death
respawns it into the trap, and the runtime recovery (correctly, no DB writes from the
runtime) cannot lift an agent whose own cell is unwalkable server-side. Next slice is
an OPERATOR-side savepoint correction (Kafra save at a verified-walkable cell — the same
class of action as today's reset, extended to `save_point_map/x/y`) or, runtime-side,
survival gating that avoids engaging near known-unwalkable own-cells. Do NOT iterate the
stuck-recovery further for this shape: its detection/bounding worked exactly as designed.

Secondary: the 3 zero-attack roamers (g00m03, g02m01, s03) covered 500-770 cells with
1-4 sightings — roam-reach toward declared clusters on their patches, unchanged class
from leg-128's sighting analysis.

— leg-129 shepherd, 2026-11-25
