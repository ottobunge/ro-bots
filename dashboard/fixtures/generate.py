"""Offline Python serializer evidence, not native gameplay or host execution.
Run from repository root: nix develop -c uv run python dashboard/fixtures/generate.py
"""
import hashlib
import json
import random
from dataclasses import replace
from pathlib import Path

from robots.adapters.worldfeed_server import WorldFeedServer, _sse
from robots.app.world_state import WorldState
from robots.society.society import ReputationEvent, SocietyRoster

root = Path(__file__).resolve().parents[2]
out = Path(__file__).resolve().parent
state = WorldState(SocietyRoster.build(random.Random(42), n_groups=3), clock=lambda: 1700000000.25)
id = sorted(state.roster.personas)[0]
state.set_agent_state(id, current_goal="grind", current_script="farm_poring.py", current_plan="fixture plan", online=True)
runtime = state.agent_state(id)
assert runtime is not None
state._agent_states[id] = replace(runtime, characters=("Fixture Character",))
rep = ReputationEvent("Fixture Human", id, 0.4, "offline fixture")
state.roster.reputation.apply_event(rep)
state.roster.reputation.propagate(rep, state.roster.graph, state.roster.groups)
state.apply_command({"type": "force_action", "persona_id": id, "action": "chat", "args": "fixture note only"})
state.push_event("combat", "fixture summary, not native evidence")
server = WorldFeedServer(state)
for name, value in [("roster.json", server.roster_snapshot()), ("agent.json", server.agent_detail(id)), ("event.json", server.feed_item_payload(state.events[-1]))]:
    (out / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
(out / "events.sse").write_text("".join(_sse(server.feed_item_payload(e), e.sequence) for e in state.events))
(out / "provenance.json").write_text(json.dumps({"evidence": "deterministic offline Python serialization; no game/DB/provider/host", "persona_id": id, "sources": {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in ["src/robots/adapters/worldfeed_server.py", "src/robots/app/world_state.py"]}}, indent=2) + "\n")
print("Generated offline Python serialization fixtures", id)
