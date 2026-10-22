"""AgentHost coordination wiring (feature/coordination-wiring).

The offline-tested society layer (RelationshipLedger + seed_roster +
GroupCoordinator/BoundCoordinator) wired into the live host: per-agent
persisted ledgers under the memory root, a LIVE online provider read from
``host.agents``, the ledger lines as the brain's social view, and the
rendezvous defaults (``prontera 156,22`` + the group's window start).
Coordination content still travels ONLY through game packets (the
anti-telepathy pins in tests/test_objectives.py stay authoritative).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from robots.adapters.chat.stub import StaticChatGenerator
from robots.app.agent_runtime import AgentHost, ManifestEntry, load_manifest, meet_when_for
from robots.app.brain import EventDrivenBrain
from robots.domain.actions import InviteToParty, Say, WhisperTo
from robots.domain.events import Heartbeat
from robots.domain.model import BotState, Goal
from robots.popgen import (
    GeneratedPopulation,
    PersonaProfile,
    PopulationSpec,
    generate_population,
)
from robots.society.models import Attitude, FriendGroup, Playstyle, Schedule, SocietyPersona
from robots.society.objectives import (
    OBJECTIVE_INVITED,
    BoundCoordinator,
    GroupCoordinator,
)
from robots.society.society import ReputationStore, SocialGraph, SocietyRoster
from tests.test_agent_host import STUB_ANSWERS, FakeGameClient, ScriptedDecisionModel

# ----------------------------------------------------------------- fixtures

WIRED_SPEC = PopulationSpec(friend_groups=1, friends_per_group=(3, 3), solo_agents=1, seed=7)


def make_population() -> GeneratedPopulation:
    """One 3-member friend group + one solo outsider (deterministic)."""
    population = generate_population(WIRED_SPEC)
    group_ids = {p.group_id for p in population.personas if p.group_id is not None}
    assert len(group_ids) == 1
    group = [p for p in population.personas if p.group_id is not None]
    assert len(group) == 3  # leader + one online mate + one away member
    assert len([p for p in population.personas if p.group_id is None]) == 1
    return population


def group_ids(population: GeneratedPopulation) -> list[str]:
    """The friend group's member ids in registration (popgen persona) order."""
    return [p.persona_id for p in population.personas if p.group_id is not None]


def population_roster(
    entries: dict[str, ManifestEntry], population: GeneratedPopulation
) -> SocietyRoster:
    """The production roster shape: one FriendGroup per popgen group, its
    schedule taken from the group's first member (the rule build_roster uses
    for configured schedule files)."""
    personas = {
        pid: SocietyPersona(
            pid,
            entry.char_name,
            Playstyle.MELEE,
            Attitude.HELPFUL_NEWBIE,
            0.5,
            (1, 99),
        )
        for pid, entry in entries.items()
    }
    groups: list[FriendGroup] = []
    graph = SocialGraph()
    by_group: dict[str, list[str]] = {}
    for persona in population.personas:
        if persona.group_id is not None:
            by_group.setdefault(persona.group_id, []).append(persona.persona_id)
    for index, (_group_id, members) in enumerate(sorted(by_group.items())):
        first = population.personas[
            next(i for i, p in enumerate(population.personas) if p.persona_id == members[0])
        ]
        schedule = Schedule(
            tuple((int(day), float(start), float(end)) for day, start, end in first.schedule)
        )
        group = FriendGroup(f"playing-{index}", tuple(members), Attitude.HELPFUL_NEWBIE, schedule)
        groups.append(group)
        graph.seed_group(group)
    for persona in population.personas:
        if persona.group_id is None:
            solo = FriendGroup(
                f"playing-{len(groups)}",
                (persona.persona_id,),
                Attitude.SOLO,
                Schedule(
                    tuple(
                        (int(day), float(start), float(end)) for day, start, end in persona.schedule
                    )
                ),
            )
            groups.append(solo)
            graph.seed_group(solo)
    return SocietyRoster(groups, personas, graph, ReputationStore())


class CapturingDecision(ScriptedDecisionModel):
    """Scripted answers that also record every received request."""

    def __init__(self, answers: dict[str, Any] | None = None) -> None:
        super().__init__(dict(STUB_ANSWERS if answers is None else answers))
        self.requests: list[dict[str, Any]] = []

    def decide(self, request: dict[str, Any]) -> dict[str, Any]:
        self.requests.append(request)
        return {"answers": dict(super().decide(request)["answers"])}


def wiring_host(
    tmp_path: Path,
    population: GeneratedPopulation | None = None,
    *,
    use_file: bool = False,
    decision_factory: Any | None = None,
    **kwargs: Any,
) -> AgentHost:
    """An offline host over the population's own manifest (popgen persona ids)."""
    population = population if population is not None else make_population()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(population.manifest))
    population_file = tmp_path / "population.json"
    population_file.write_text(json.dumps(population.summary(), indent=1) + "\n")
    host = AgentHost(
        population_roster(load_manifest(str(manifest_path)), population),
        str(manifest_path),
        chat_generator=StaticChatGenerator(),
        client_factory=FakeGameClient,
        decision_factory=decision_factory,
        run_worldfeed=False,
        memory_root=tmp_path / "memory",
        population_file=str(population_file) if use_file else None,
        population=None if use_file else population,
        **kwargs,
    )
    for agent in host.agents.values():
        agent._threaded = False
    return host


def make_state(**overrides: object) -> BotState:
    """A deterministic BotState (mirrors tests/test_objectives.py)."""
    base: dict[str, Any] = {
        "name": "PartyLeader",
        "job": "Swordsman",
        "base_level": 42,
        "hp": 800,
        "max_hp": 1000,
        "sp": 60,
        "max_sp": 80,
        "map_name": "prontera",
        "x": 150,
        "y": 143,
        "goal": Goal.GRIND,
        "in_party": False,
        "nearby": (),
        "inventory": {"Red Potion": 5},
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(overrides)
    return BotState(**base)


# ------------------------------------------------------------- the null case


def test_host_without_population_keeps_coordination_none(tmp_path: Path) -> None:
    population = make_population()
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(population.manifest))
    host = AgentHost(
        population_roster(load_manifest(str(manifest_path)), population),
        str(manifest_path),
        chat_generator=StaticChatGenerator(),
        client_factory=FakeGameClient,
        run_worldfeed=False,
    )
    try:
        for agent in host.agents.values():
            brain = agent.brain
            assert isinstance(brain, EventDrivenBrain)
            assert brain._coordination is None
            assert brain._social_view is None
        relations_dir = tmp_path / "memory" / "relations"
        assert not relations_dir.exists()
    finally:
        host.stop()


# ------------------------------------------------------------ the wired case


def test_population_wires_coordinator_social_view_and_ledger_files(tmp_path: Path) -> None:
    population = make_population()
    host = wiring_host(tmp_path, population)
    try:
        assert set(host.agents) == {p.persona_id for p in population.personas}
        for persona in population.personas:
            agent = host.agents[persona.persona_id]
            brain = agent.brain
            assert isinstance(brain, EventDrivenBrain)
            assert isinstance(brain._coordination, BoundCoordinator)
            assert brain._social_view is not None
            ledger_file = tmp_path / "memory" / "relations" / f"{persona.persona_id}.json"
            assert ledger_file.is_file()
        leader = host.agents[group_ids(population)[0]]
        brain = leader.brain
        assert isinstance(brain, EventDrivenBrain)
        assert brain._social_view is not None
        lines = list(brain._social_view())
        assert any(line.startswith("your group pop_") for line in lines)
    finally:
        host.stop()


def test_population_file_option_wires_the_same_way(tmp_path: Path) -> None:
    population = make_population()
    host = wiring_host(tmp_path, population, use_file=True)
    try:
        leader = host.agents[group_ids(population)[0]]
        brain = leader.brain
        assert isinstance(brain, EventDrivenBrain)
        assert isinstance(brain._coordination, BoundCoordinator)
        assert brain._social_view is not None
        assert (tmp_path / "memory" / "relations" / f"{leader.persona.persona_id}.json").is_file()
    finally:
        host.stop()


def test_coordination_online_provider_reads_live_state(tmp_path: Path) -> None:
    population = make_population()
    host = wiring_host(tmp_path, population)
    try:
        leader_id, mate_id = group_ids(population)[:2]
        leader_brain = host.agents[leader_id].brain
        assert isinstance(leader_brain, EventDrivenBrain)
        coordination = leader_brain._coordination
        assert isinstance(coordination, BoundCoordinator)
        # Nobody connected: no window, no question.
        assert coordination.formation_question() is None
        # Both members come online (plain state poke: no client needed).
        host.agents[leader_id].online = True
        host.agents[mate_id].online = True
        question = coordination.formation_question()
        assert question is not None
        assert "hunt" in question["criteria"]
        # The mate drops again: the provider re-reads host.agents, no caching.
        host.agents[mate_id].online = False
        assert coordination.formation_question() is None
    finally:
        host.stop()


def test_decide_request_carries_the_formation_question_and_social_lines(
    tmp_path: Path,
) -> None:
    population = make_population()
    model = CapturingDecision()
    leader_id, mate_id = group_ids(population)[:2]
    host = wiring_host(tmp_path, population, decision_factory=lambda: model)
    try:
        leader = host.agents[leader_id]
        assert leader.connect()  # real FakeGameClient session; online=True
        host.agents[mate_id].online = True  # the group window opens (live provider)
        leader_brain = leader.brain
        assert isinstance(leader_brain, EventDrivenBrain)
        leader_brain.handle_event(leader.build_state(), Heartbeat(seq=1))
        assert model.requests
        request = model.requests[-1]
        assert "objective_action" in request["questions"]
        assert "hunt" in request["questions"]["objective_action"]["criteria"]
        assert "social_relations" in request["state"]
        assert "your group pop_" in request["state"]["social_relations"]
    finally:
        host.stop()


# ------------------------------------------- the rendezvous + packet emission


def test_meet_when_derives_the_group_window_start() -> None:
    def persona(
        persona_id: str, group_id: str | None, schedule: tuple[tuple[int, float, float], ...]
    ) -> PersonaProfile:
        return PersonaProfile(
            persona_id=persona_id,
            name=persona_id.title(),
            account=persona_id,
            password="pw",
            pincode="0000",
            sex="M",
            group_id=group_id,
            playstyle="grinder",
            build="swordman-grinder",
            schedule=schedule,
            save_map="prontera",
            save_point=(150, 143),
        )

    leader = persona("g_lead", "g1", ((2, 17.75, 20.5), (0, 19.0, 21.0)))
    mate = persona("g_mate", "g1", ((2, 17.5, 19.0),))
    solo = persona("s1", None, ((1, 9.25, 12.0),))
    population = GeneratedPopulation(
        spec=PopulationSpec(1, (2, 2), 1, 1),
        personas=(leader, mate, solo),
        fixture_sql="",
        manifest={},
    )
    # The group's window start: the FIRST registered member's first window.
    assert meet_when_for("g_lead", population) == "17:45"
    assert meet_when_for("g_mate", population) == "17:45"
    # A solo derives from its own first window (the coordination stays inert).
    assert meet_when_for("s1", population) == "09:15"
    assert meet_when_for("absent", population) is None


def test_formed_objective_emits_invites_and_the_derived_rendezvous(tmp_path: Path) -> None:
    population = make_population()
    members = group_ids(population)
    leader_id, mate_id, away_id = members[0], members[1], members[2]
    host = wiring_host(tmp_path, population)
    try:
        host.agents[leader_id].online = True
        host.agents[mate_id].online = True
        leader_brain = host.agents[leader_id].brain
        assert isinstance(leader_brain, EventDrivenBrain)
        coordination = leader_brain._coordination
        assert isinstance(coordination, BoundCoordinator)
        assert isinstance(coordination._coordinator, GroupCoordinator)
        leader_persona = next(p for p in population.personas if p.persona_id == leader_id)
        day, start, _end = leader_persona.schedule[0]
        del day
        expected_when = f"{int(start):02d}:{round((start % 1) * 60):02d}"
        away_name = next(p.name for p in population.personas if p.persona_id == away_id)

        answers = dict(STUB_ANSWERS)
        answers["objective_action"] = {"type": "choice", "choice": "hunt", "confidence": 0.9}
        answers["farm_target"] = {"type": "choice", "choice": "porings", "confidence": 0.9}
        leader_brain._model._answers = dict(answers)  # type: ignore[attr-defined]
        result = leader_brain.handle_event(make_state(), Heartbeat(seq=1))
        invites = [a for a in result.actions if isinstance(a, InviteToParty)]
        assert len(invites) == 1
        assert any(isinstance(a, Say) and "join me" in a.text for a in result.actions)
        live = coordination.book.live_objectives()
        assert len(live) == 1
        assert live[0].status == OBJECTIVE_INVITED

        # The away member reconnects: the recorded rendezvous is delivered as
        # a real in-game whisper naming the derived group window start.
        host.agents[away_id].online = True
        result = leader_brain.handle_event(make_state(), Heartbeat(seq=2))
        whispers = [a for a in result.actions if isinstance(a, WhisperTo)]
        assert any(
            whisper.to == away_name
            and whisper.text == f"meet at prontera 156,22 at {expected_when}"
            for whisper in whispers
        )
    finally:
        host.stop()


def test_ledger_persists_objectives_across_host_restarts(tmp_path: Path) -> None:
    population = make_population()
    members = group_ids(population)
    leader_id, mate_id = members[0], members[1]
    host = wiring_host(tmp_path, population)
    try:
        host.agents[leader_id].online = True
        host.agents[mate_id].online = True
        leader_brain = host.agents[leader_id].brain
        assert isinstance(leader_brain, EventDrivenBrain)
        coordination = leader_brain._coordination
        assert isinstance(coordination, BoundCoordinator)
        answers = dict(STUB_ANSWERS)
        answers["objective_action"] = {"type": "choice", "choice": "hunt", "confidence": 0.9}
        leader_brain._model._answers = dict(answers)  # type: ignore[attr-defined]
        leader_brain.handle_event(make_state(), Heartbeat(seq=1))
        assert coordination.book.live_objectives()
    finally:
        host.stop()

    restored = wiring_host(tmp_path, population)
    try:
        restored_brain = restored.agents[leader_id].brain
        assert isinstance(restored_brain, EventDrivenBrain)
        restored_coordination = restored_brain._coordination
        assert isinstance(restored_coordination, BoundCoordinator)
        live = restored_coordination.book.live_objectives()
        assert len(live) == 1
        assert live[0].status == OBJECTIVE_INVITED
    finally:
        restored.stop()


def test_solo_agent_never_receives_a_formation_question(tmp_path: Path) -> None:
    population = make_population()
    host = wiring_host(tmp_path, population)
    try:
        solo_id = next(p.persona_id for p in population.personas if p.group_id is None)
        solo_brain = host.agents[solo_id].brain
        assert isinstance(solo_brain, EventDrivenBrain)
        coordination = solo_brain._coordination
        assert isinstance(coordination, BoundCoordinator)
        host.agents[solo_id].online = True
        for other in host.agents.values():
            other.online = True
        assert coordination.formation_question() is None
    finally:
        host.stop()
