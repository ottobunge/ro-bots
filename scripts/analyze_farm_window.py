#!/usr/bin/env python3
"""Read-only farm-window census. No services or database connections.

Usage: python scripts/analyze_farm_window.py TRACE_DIR > census.json
Bounds are UTC, half-open. Response durations are clipped to the window;
requests provide event provenance, never successful-choice counts. Receipt
snapshots are intentionally not summed (their gate tails repeat).
"""

import argparse
import collections
import json
import pathlib
import statistics
from datetime import datetime


def census(trace_dir, start, end):
    lower, upper = map(lambda value: datetime.fromisoformat(value).timestamp(), (start, end))
    agents = {}
    for path in sorted(pathlib.Path(trace_dir).glob("*.jsonl")):
        choices = collections.Counter()
        goals = collections.Counter()
        gates = collections.Counter()
        events = collections.Counter()
        scripts = collections.Counter()
        durations = []
        blocked = collections.Counter()
        swings = collections.defaultdict(list)
        damage = []
        authored = sent = errors = 0
        request = {}
        for line in path.open():
            # Existing traces have a fixed leading t field. Avoid parsing old
            # multi-day payloads except the request that carries provenance.
            stamp = line[7:32]
            if stamp < start[:19] and '"kind": "decide_request"' not in line:
                continue
            if stamp >= end[:19]:
                continue
            row = json.loads(line)
            at = datetime.fromisoformat(row["t"]).timestamp()
            kind = row["kind"]
            if kind == "decide_request":
                request = row["request"]
            if at < lower:
                continue
            if kind == "decide_response":
                duration = row.get("duration_s", 0)
                clipped = max(0, min(at, upper) - max(lower, at - duration))
                event = request.get("state", {}).get("event", "unknown")
                event = "chat" if " said: " in event else event.split(" ")[0]
                blocked[event] += clipped
                durations.append(duration)
                if row.get("error"):
                    errors += 1
                else:
                    choices[
                        row.get("answers", {}).get("next_action", {}).get("choice", "missing")
                    ] += 1
            elif kind == "goal_review":
                goals[row["goal"]] += 1
            elif kind == "world_event":
                events[row["event"]] += 1
            elif kind == "script_step":
                scripts[row["script"] + ":" + ",".join(row["actions"])] += 1
            elif kind == "action_executed" and row["action"] == "Attack":
                authored += 1
            elif kind == "swing_observation":
                event = row["event"]
                if event == "attack_refused":
                    gates[row["reason"]] += 1
                elif event == "swing":
                    sent += 1
                    swings[row["target_id"]].append(row["at"])
                elif (
                    event == "damage"
                    and row["source_id"] == row["own_id"]
                    and not row.get("is_sp_damage")
                ):
                    amount = max(0, row["damage"]) + max(0, row.get("damage2", 0))
                    if amount:
                        damage.append(amount)
        agents[path.stem] = dict(
            choices=dict(choices),
            goal_reviews=dict(goals),
            decide_errors=errors,
            decide_completed=len(durations),
            decide_seconds=round(sum(blocked.values()), 3),
            decide_by_event_seconds={k: round(v, 3) for k, v in blocked.items()},
            decide_median_s=statistics.median(durations) if durations else None,
            events=dict(events),
            sampled_scripts=dict(scripts),
            attacks_authored=authored,
            swings=sent,
            attack_refusals=dict(gates),
            positive_own_hits=len(damage),
            damage_total=sum(damage),
            damage_values=damage,
            same_target_swing_gaps_s=[
                round(b - a, 3) for times in swings.values() for a, b in zip(times, times[1:])
            ],
        )
    return dict(start=start, end=end, agents=agents)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace_dir")
    parser.add_argument("--start", default="2026-11-23T19:00:00+00:00")
    parser.add_argument("--end", default="2026-11-23T20:30:00+00:00")
    args = parser.parse_args()
    print(json.dumps(census(args.trace_dir, args.start, args.end), indent=2))
