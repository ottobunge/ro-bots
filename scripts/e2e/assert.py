#!/usr/bin/env python3
"""e2e-assert: the modest first bar over ONE e2e window receipt.

Judged honestly, from named fields of the newest receipt under
.work/playing-grind-emission/evidence/ in this worktree:

  1. the receipt exists, parses, and belongs to THIS world's manifest with the
     bounded e2e duration;
  2. the logins landed: every reported agent shows a healthy transport and at
     least one own-position ingest (the map-entry proof);
  3. progress: at least one agent whose position left the fixture start cell
     OR with at least one accepted decision.

What ran is printed per agent (decisions, failures, dispatched actions,
positions, engagement floor) — a quiet receipt cannot pass silently.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def counter(value: Any) -> int:
    if isinstance(value, dict):
        return int(value.get("count") or 0)
    return int(value or 0)


def main(argv: list[str] | None = None) -> int:
    repo = Path(sys.argv[1] if argv is None else argv[0]).resolve()
    fixture = json.load(open(sys.argv[2], encoding="utf-8"))
    manifest = sys.argv[3]
    duration = float(sys.argv[4])

    evidence = repo / ".work" / "playing-grind-emission" / "evidence"
    receipts = sorted(evidence.glob("receipt-*.json"))
    if not receipts:
        print(f"e2e-assert: FAIL: no receipt under {evidence}", file=sys.stderr)
        return 1
    receipt_path = receipts[-1]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))

    checks: list[tuple[str, bool, str]] = []
    scope = receipt.get("run_scope", {})
    checks.append((
        "receipt exists and parses",
        True,
        str(receipt_path),
    ))
    scope_manifest = str(scope.get("manifest", ""))
    checks.append((
        "receipt belongs to the e2e world manifest",
        scope_manifest.endswith(manifest),
        f"{scope_manifest or 'missing'} vs {manifest}",
    ))
    scope_duration = float(scope.get("duration_s") or 0)
    checks.append((
        f"bounded duration ~= {duration:g}s",
        abs(scope_duration - duration) <= max(30.0, duration * 0.2),
        f"run_scope.duration_s={scope_duration:g}",
    ))

    agents = receipt.get("agents", {})
    if not agents:
        checks.append(("receipt reports agents", False, "agents dict empty"))
    else:
        landed = []
        floor_met = []
        for persona, entry in sorted(agents.items()):
            transport = str(entry.get("transport_state"))
            own_pos = int((entry.get("frame_counters") or {}).get("own_position_ingests") or 0)
            healthy = transport == "healthy" and own_pos > 0
            landed.append((persona, healthy, transport, own_pos))
            floor_met.append((persona, str(entry.get("engagement_floor"))))

        for persona, healthy, transport, own_pos in landed:
            checks.append((
                f"login landed: {persona}",
                healthy,
                f"transport_state={transport} own_position_ingests={own_pos}",
            ))

        # progress: position left the start cell OR decisions happened
        progress_details = []
        any_progress = False
        by_persona = {str(a["persona_id"]): a for a in fixture["accounts"]}
        for persona, entry in sorted(agents.items()):
            diag = entry.get("runtime_diagnostic") or {}
            position = diag.get("position") or [None, None]
            map_name = str(diag.get("map_name") or "")
            start = by_persona.get(persona, {}).get("start", {})
            left_start = (
                map_name and start
                and (map_name.split(".")[0] != str(start.get("last_map"))
                     or position[0] != start.get("last_x")
                     or position[1] != start.get("last_y"))
            )
            decides = counter(entry.get("decision_calls"))
            counts = (entry.get("dispatched_actions") or {}).get("count") or {}
            dispatched = sum(
                counter(counts.get(kind)) for kind in ("attack", "moveTo", "loot", "rest", "other")
            )
            any_progress = any_progress or bool(left_start) or decides > 0
            progress_details.append(
                f"{persona}: pos={position} on {map_name or '?'} "
                f"(start {start.get('last_map')} {start.get('last_x')},{start.get('last_y')}), "
                f"decisions={decides} (failures={counter(entry.get('decision_failures'))}), "
                f"dispatched={dispatched}, floor={dict(floor_met).get(persona)}"
            )
        checks.append((
            "progress: a position changed OR decisions happened",
            any_progress,
            "; ".join(progress_details),
        ))

    failed = [c for c in checks if not c[1]]
    print(f"e2e-assert: receipt {receipt_path.name}")
    for name, ok, detail in checks:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}" + (f" — {detail}" if detail else ""))
    if failed:
        print(f"e2e-assert: FAIL ({len(failed)} of {len(checks)} checks failed)", file=sys.stderr)
        return 1
    print("e2e-assert: PASS — modest first bar met (what ran is itemized above)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
