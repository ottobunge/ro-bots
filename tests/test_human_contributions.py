"""Human-player contribution tracking (feature/human-contribution).

The human friendship score end to end: the wire observations (damage /
skill-use / party exp rows naming a party member) folded into the
RelationshipLedger's human contribution score, the dead-weight windows, the
review-cadence gossip hop to allied groups WITH the report leaving only as an
in-game party/public chat premade (the anti-telepathy channel), the decide
context carrying the standing, and the per-agent runtime wiring.
"""

import json
import struct
from typing import Any

import pytest

from robots.adapters.chat.stub import StaticChatGenerator
from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.app.agent_runtime import AgentHost, ManifestEntry, ScheduledAgent, load_manifest
from robots.app.brain import EventDrivenBrain
from robots.app.playing_runtime import PlayingClient
from robots.domain.actions import PartyChat, Say
from robots.domain.events import Heartbeat
from robots.domain.model import PartyObservation
from robots.society.contributions import (
    DEAD_WEIGHT_WINDOW_S,
    HumanContributionObserver,
)
from robots.society.models import Attitude, Playstyle, SocietyPersona
from robots.society.relations import (
    CONTRIBUTION_KINDS,
    CONTRIBUTION_UP,
    DEAD_WEIGHT_DELTA,
    GOSSIP_HOP_DECAY,
    GOSSIP_THRESHOLD,
    PARTY_AFFINITY_PER_HOUR,
    WEEKLY_HALF_LIFE_S,
    RelationshipLedger,
    human_report_line,
)
from tests.test_agent_host import FakeGameClient
from tests.test_brain import base_answers
from tests.test_coordination_wiring import make_population, population_roster, wiring_host
from tests.test_playing_runtime import Wire
from tests.test_relations import CapturingModel, make_state

BOT_AID = 999
TRADER_AID = 4242
MATE_AID = 888
MOB_AID = 555
PARTY = {"Botnyan": BOT_AID, "Trader": TRADER_AID, "Groupmate": MATE_AID}


def damage(source: int = TRADER_AID, target: int = MOB_AID, amount: int = 220) -> PartyObservation:
    return PartyObservation(kind="damage", source_id=source, target_id=target, amount=amount)


def skill(
    source: int = TRADER_AID,
    target: int = MATE_AID,
    skill_id: int = 28,
    *,
    failed: bool = False,
) -> PartyObservation:
    return PartyObservation(
        kind="skill", source_id=source, target_id=target, amount=0, skill_id=skill_id, failed=failed
    )


def exp(delta: int = 40) -> PartyObservation:
    return PartyObservation(kind="exp", source_id=0, target_id=0, amount=delta)


def wired(*, ts: float = 0.0) -> tuple[RelationshipLedger, HumanContributionObserver]:
    """The acceptance ledger: my group, an allied group, a solo-free world."""
    ledger = RelationshipLedger()
    ledger.register_persona("me", "Botnyan")
    ledger.register_persona("mate", "Groupmate")
    ledger.register_persona("ally", "Allynyan")
    ledger.seed_group("pop_g00", ("me", "mate"))
    ledger.seed_group("pop_g01", ("ally", "ally2"))
    ledger.record_party_time(["me", "ally"], seconds=5 * 3600, ts=0.0)
    return ledger, HumanContributionObserver(ledger, "me", clock=lambda: ts)


# -- observation -> scoring -------------------------------------------------


def test_human_damage_on_a_monster_raises_score() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(damage(),), ts=10.0)
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP)


def test_agent_party_members_are_never_credited_as_humans() -> None:
    ledger, observer = wired()
    observer.observe(
        party=PARTY, observations=(damage(source=BOT_AID), damage(source=MATE_AID)), ts=10.0
    )
    assert ledger.human_score("Botnyan") == 0.0
    assert ledger.human_score("Groupmate") == 0.0


def test_damage_targeting_a_party_member_is_not_contribution() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(damage(target=MATE_AID),), ts=10.0)
    assert ledger.human_score("Trader") == 0.0


def test_heal_and_buff_skill_rows_raise_score() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(skill(), skill(skill_id=34)), ts=10.0)
    assert ledger.human_score("Trader") == pytest.approx(2 * CONTRIBUTION_UP)


def test_failed_skill_use_is_not_contribution() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(skill(failed=True),), ts=10.0)
    assert ledger.human_score("Trader") == 0.0


def test_exp_share_participation_credits_present_humans() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(exp(delta=40),), ts=10.0)
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP)
    assert "exp_share" in CONTRIBUTION_KINDS


def test_exp_share_without_party_humans_credits_nobody() -> None:
    ledger, observer = wired()
    observer.observe(
        party={"Botnyan": BOT_AID, "Groupmate": MATE_AID}, observations=(exp(),), ts=10.0
    )
    assert ledger.human_score("Trader") == 0.0
    assert ledger.human_score("Groupmate") == 0.0


def test_score_clamps_at_design_bounds() -> None:
    ledger, observer = wired()
    observer.observe(party=PARTY, observations=(damage(),) * 20, ts=10.0)
    assert ledger.human_score("Trader") == 1.0


# -- presence and dead weight ------------------------------------------------


def test_quiet_presence_is_dead_weight_on_review() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, ts=0.0)
    reports = observer.review(ts=DEAD_WEIGHT_WINDOW_S)
    assert reports == ()  # dead weight alone does not cross the gossip threshold
    assert ledger.human_score("Trader") == pytest.approx(DEAD_WEIGHT_DELTA)


def test_dead_weight_window_does_not_double_count() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, ts=0.0)
    observer.review(ts=DEAD_WEIGHT_WINDOW_S)
    observer.review(ts=DEAD_WEIGHT_WINDOW_S + 1.0)
    # The window restarted at the last review: one second of quiet is not a window.
    assert ledger.human_score("Trader") == pytest.approx(DEAD_WEIGHT_DELTA)


def test_contributing_human_is_not_dead_weight() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, ts=0.0)  # joins
    observer.observe(party=PARTY, observations=(damage(),), ts=DEAD_WEIGHT_WINDOW_S / 2)
    observer.review(ts=DEAD_WEIGHT_WINDOW_S)  # only half a window since the assist
    half_factor = 0.5 ** ((DEAD_WEIGHT_WINDOW_S / 2) / WEEKLY_HALF_LIFE_S)
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP * half_factor)


def test_departed_human_leaves_the_presence_windows() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, ts=0.0)
    observer.observe(party={"Botnyan": BOT_AID}, ts=10.0)
    observer.review(ts=DEAD_WEIGHT_WINDOW_S)
    assert ledger.human_score("Trader") == 0.0  # left before any window elapsed


# -- review-cadence propagation ----------------------------------------------


def test_material_report_propagates_to_allied_group_and_names_the_human() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, observations=(damage(),), ts=0.0)
    reports = observer.review(ts=0.0)  # same instant: no decay anywhere
    assert len(reports) == 1
    report = reports[0]
    assert report.human_name == "Trader"
    assert report.delta == pytest.approx(CONTRIBUTION_UP)
    assert "Trader" in report.line
    # The reviewed verdict reached the group rows: own group full weight, the
    # allied group at the decayed gossip hop.
    assert ledger.group_reputation("pop_g00", "Trader") == pytest.approx(CONTRIBUTION_UP)
    affinity = 5 * PARTY_AFFINITY_PER_HOUR
    expected = CONTRIBUTION_UP * GOSSIP_HOP_DECAY * (0.5 + 0.5 * affinity)
    assert ledger.group_reputation("pop_g01", "Trader") == pytest.approx(expected)


def test_negative_report_propagates_the_same_way() -> None:
    ledger, observer = wired(ts=0.0)
    window_factor = 0.5 ** (DEAD_WEIGHT_WINDOW_S / WEEKLY_HALF_LIFE_S)
    observer.observe(party=PARTY, ts=0.0)
    assert observer.review(ts=DEAD_WEIGHT_WINDOW_S) == ()  # one step: below threshold
    assert observer.review(ts=2 * DEAD_WEIGHT_WINDOW_S) == ()  # two: still just under
    reports = observer.review(ts=3 * DEAD_WEIGHT_WINDOW_S)  # three: material
    assert len(reports) == 1
    report = reports[0]
    # Three dead-weight steps, each earlier one decayed by one window more.
    expected = DEAD_WEIGHT_DELTA * (window_factor**2 + window_factor + 1)
    assert report.delta == pytest.approx(expected)
    assert report.delta < 0
    assert ledger.human_score("Trader") == pytest.approx(expected)
    assert ledger.group_reputation("pop_g00", "Trader") == pytest.approx(expected)
    affinity = 5 * PARTY_AFFINITY_PER_HOUR * window_factor**3  # as of the review instant
    hop = expected * GOSSIP_HOP_DECAY * (0.5 + 0.5 * affinity)
    assert ledger.group_reputation("pop_g01", "Trader") == pytest.approx(hop)
    assert observer.review(ts=4 * DEAD_WEIGHT_WINDOW_S) == ()  # already told


def test_small_delta_stays_local_without_report() -> None:
    ledger, observer = wired(ts=0.0)
    ledger.record_contribution("Trader", "dead_weight", ts=0.0)  # -0.1: below threshold
    reports = observer.review(ts=10.0)
    assert reports == ()
    assert ledger.group_reputation("pop_g00", "Trader") == 0.0


def test_report_queue_drains_once() -> None:
    _ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, observations=(damage(),), ts=10.0)
    assert len(observer.review(ts=20.0)) == 1
    assert observer.review(ts=30.0) == ()


def test_solo_agent_reports_without_a_group_row() -> None:
    ledger = RelationshipLedger()
    ledger.register_persona("me", "Botnyan")
    observer = HumanContributionObserver(ledger, "me", clock=lambda: 0.0)
    observer.observe(
        party={"Botnyan": BOT_AID, "Trader": TRADER_AID}, observations=(damage(),), ts=1.0
    )
    reports = observer.review(ts=2.0)
    assert len(reports) == 1  # the in-game line still leaves
    assert ledger.human_score("Trader") == pytest.approx(CONTRIBUTION_UP)
    assert ledger.group_reputation("pop_g00", "Trader") == 0.0


def test_report_line_premade_names_the_human() -> None:
    good = human_report_line("Trader", GOSSIP_THRESHOLD)
    bad = human_report_line("Leecher", -GOSSIP_THRESHOLD)
    assert "Trader" in good
    assert "Leecher" in bad
    assert good != bad


# -- decide context -----------------------------------------------------------


def test_party_human_standing_reaches_the_decide_context() -> None:
    ledger, observer = wired(ts=0.0)
    observer.observe(party=PARTY, observations=(damage(),), ts=10.0)
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(
        decision_model=model,
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: (*ledger.context_lines("me"), *observer.party_human_lines()),
    )
    brain.handle_event(make_state(), Heartbeat(seq=1))
    relations = model.requests[0]["state"]["social_relations"]
    assert "human Trader +0.20" in relations  # the ledger's standing line
    assert "party human Trader +0.20" in relations  # the observer's presence line
    # Groupmate is a roster agent: it shows in the group line, never as a human.
    assert "party human Groupmate" not in relations
    assert "Groupmate +0.50" in relations


def test_party_human_lines_are_bounded_and_score_ordered() -> None:
    _ledger, observer = wired(ts=0.0)
    party = dict(PARTY)
    for i in range(6):
        party[f"Human{i}"] = 7000 + i
    observer.observe(party=party, observations=(damage(),), ts=1.0)
    assert len(observer.party_human_lines()) <= 4
    assert observer.party_human_lines()[0].startswith("party human Trader")


# -- anti-telepathy: the report is an in-game chat action ---------------------


def test_report_leaves_as_party_chat_and_never_mutates_other_ledgers() -> None:
    ledger, observer = wired(ts=0.0)
    ally_ledger, _ = wired(ts=0.0)  # the allied agent's own ledger
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=[base_answers(), base_answers()]),
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: (*ledger.context_lines("me"), *observer.party_human_lines()),
        human_reports=observer.review,
    )
    brain.start(make_state())  # the start review drains an empty queue
    observer.observe(party=PARTY, observations=(damage(),), ts=10.0)
    result = brain.handle_event(make_state(in_party=True), Heartbeat(seq=1))
    chats = [a for a in result.actions if isinstance(a, PartyChat)]
    assert len(chats) == 1
    assert "Trader" in chats[0].text
    assert chats[0].text == human_report_line("Trader", CONTRIBUTION_UP)
    # Anti-telepathy: the allied agent's ledger is untouched by my review —
    # only the chat line crossed the wire; they update from what they HEAR.
    assert ally_ledger.human_score("Trader") == 0.0
    assert ally_ledger.group_reputation("pop_g01", "Trader") == 0.0
    assert ledger.group_reputation("pop_g01", "Trader") != 0.0  # my own belief moved


def test_report_says_publicly_outside_a_party() -> None:
    _ledger, observer = wired(ts=0.0)
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=[base_answers(), base_answers()]),
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: (),
        human_reports=observer.review,
    )
    brain.start(make_state())
    observer.observe(party=PARTY, observations=(damage(),), ts=10.0)
    result = brain.handle_event(make_state(in_party=False), Heartbeat(seq=1))
    says = [a for a in result.actions if isinstance(a, Say)]
    assert len(says) == 1
    assert "Trader" in says[0].text


def test_no_pending_report_no_chat() -> None:
    _ledger, observer = wired(ts=0.0)
    brain = EventDrivenBrain(
        decision_model=ScriptedDecisionModel(queue=[base_answers()]),
        chat=StaticChatGenerator(["gg"]),
        social_view=lambda: (),
        human_reports=observer.review,
    )
    brain.start(make_state())
    result = brain.handle_event(make_state(in_party=True), Heartbeat(seq=1))
    assert not [a for a in result.actions if isinstance(a, (PartyChat, Say))]


def test_brain_without_human_reports_keeps_legacy_review() -> None:
    model = CapturingModel(base_answers())
    brain = EventDrivenBrain(decision_model=model, chat=StaticChatGenerator(["gg"]))
    result = brain.handle_event(make_state(), Heartbeat(seq=1))
    assert not [a for a in result.actions if isinstance(a, (PartyChat, Say))]
    assert "human" not in model.requests[0]["state"].get("social_relations", "")


# -- the wire-facing drain (PlayingClient) ------------------------------------


def damage_frame(source: int, target: int, amount: int = 220) -> bytes:
    raw = bytearray(34)
    raw[0:2] = b"\xc8\x08"  # 0x08C8
    raw[2:6] = source.to_bytes(4, "little")
    raw[6:10] = target.to_bytes(4, "little")
    raw[22:26] = amount.to_bytes(4, "little")
    raw[29] = 0
    return bytes(raw)


def skill_wire_frame(skill_id: int = 28, target: int = MATE_AID, source: int = TRADER_AID) -> bytes:
    raw = bytearray(17)
    raw[0:2] = b"\xcb\x09"  # 0x09CB
    raw[2:4] = skill_id.to_bytes(2, "little")
    raw[4:6] = (9).to_bytes(2, "little")
    raw[6:10] = target.to_bytes(4, "little")
    raw[10:14] = source.to_bytes(4, "little")
    raw[14] = 0
    return bytes(raw)


def xp_wire_frame(param: int, value: int) -> bytes:
    return struct.pack("<HHq", 0x0ACB, param, value)


def test_playing_client_drains_party_observation_rows_once() -> None:
    wire = Wire()
    client = PlayingClient(wire)
    client.drain_native_events()  # consume the fixture frames; establish the tracker
    wire.add(
        damage_frame(TRADER_AID, MOB_AID),
        skill_wire_frame(),
        xp_wire_frame(1, 10),
        xp_wire_frame(1, 25),
    )
    client.drain_native_events()  # the tick's regular observe: pumps frames into the view
    rows = client.drain_party_observations()
    by_kind = [row.kind for row in rows]
    assert by_kind.count("damage") == 1
    assert by_kind.count("skill") == 1
    assert by_kind.count("exp") == 1
    dealt = next(row for row in rows if row.kind == "damage")
    assert (dealt.source_id, dealt.target_id, dealt.amount) == (TRADER_AID, MOB_AID, 220)
    heal = next(row for row in rows if row.kind == "skill")
    assert (heal.source_id, heal.target_id, heal.skill_id) == (TRADER_AID, MATE_AID, 28)
    shared = next(row for row in rows if row.kind == "exp")
    assert shared.amount == 15  # the positive xp delta only
    assert client.drain_party_observations() == ()  # the cursor drains once


# -- the runtime wiring (host + agent tick) -----------------------------------


def test_agent_tick_folds_wire_observations_into_the_ledger() -> None:
    now = [0.0]
    wire = Wire()
    # The live party roster (ZC_GROUP_LIST shape): the bot + one human.
    wire.party_members = [
        {"aid": BOT_AID, "gid": 1, "name": "Botnyan", "leader": 1},
        {"aid": TRADER_AID, "gid": 2, "name": "Trader", "leader": 0},
    ]
    wire.add(damage_frame(TRADER_AID, MOB_AID), skill_wire_frame())
    client = PlayingClient(wire, monotonic=lambda: now[0])
    ledger = RelationshipLedger()
    ledger.register_persona("me", "Botnyan")  # the roster: Botnyan is an agent
    observer = HumanContributionObserver(ledger, "me", clock=lambda: now[0])
    persona = SocietyPersona("me", "Botnyan", Playstyle.MELEE, Attitude.GRINDER, 0.5, (1, 10))
    agent = ScheduledAgent(
        persona,
        ManifestEntry("me", "unused", "unused", "Botnyan"),
        client=client,
        threaded=False,
        human_observer=observer,
    )
    agent.brain = EventDrivenBrain(ScriptedDecisionModel(), StaticChatGenerator(["gg"]))
    for second in range(3):
        now[0] = float(second)
        agent.tick()
    # The wire rows became scores; the bot's own rows never self-credit.
    assert ledger.human_score("Trader") == pytest.approx(2 * CONTRIBUTION_UP)
    assert ledger.human_score("Botnyan") == 0.0
    assert observer.party_human_lines() == ["party human Trader +0.40"]


def test_host_wires_observer_report_channel_and_party_lines(tmp_path: Any) -> None:
    host = wiring_host(tmp_path, make_population())
    try:
        assert host.agents
        for agent in host.agents.values():
            brain = agent.brain
            assert isinstance(brain, EventDrivenBrain)
            assert agent.human_observer is not None
            # Bound methods compare equal (new object per attribute access).
            assert brain._human_reports == agent.human_observer.review
            social_view = brain._social_view
            assert social_view is not None
            lines = social_view()
            assert isinstance(lines, tuple)  # the social view stays a line tuple
    finally:
        host.stop()


def test_host_without_population_keeps_the_observer_none(tmp_path: Any) -> None:
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
            assert agent.human_observer is None
    finally:
        host.stop()
