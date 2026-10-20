"""Finite offline NPC planning contract; no execution/native acceptance."""

import json
from dataclasses import replace
from typing import Any

import pytest

from robots.app.llm_planner import LlmPlanner, PlanningError, _schemas, decode_plan, strict_json
from robots.app.plan_lifecycle import PlanLifecycle
from robots.app.planning_context import ObservationSnapshot
from robots.domain.npc import NpcDialogue
from robots.domain.planning import Capabilities, NpcObservation, PhaseKind, PlanningRequest
from tests.test_llm_planner import ScriptedModel, frame, plan_arguments
from tests.test_plan_lifecycle import FakeClock
from tests.test_planning_context import IDENTITY, fixture_reader


def npc_arguments(operation: str = "next") -> dict[str, Any]:
    arguments = plan_arguments()
    intent: dict[str, Any] = {
        "operation": operation,
        "npc_id": 321,
        "epoch": IDENTITY.session_epoch,
        "map_name": "prontera",
        "opened_sequence": 1,
        "prompt_sequence": 5,
        "expected_stage": "next" if operation == "next" else "menu",
    }
    if operation == "choose":
        intent["option_index"] = 3
    arguments.update(
        phases=[{"kind": "npc", "map_name": "prontera", "npc_intent": intent}],
        success="npc ui advanced",
        progress="npc ui advanced",
        required_facts=[],
    )
    return arguments


def request_from(owner: PlanLifecycle) -> PlanningRequest:
    request = owner.request("received NPC guidance")
    assert request is not None
    return request


def legacy_caps() -> Capabilities:
    return Capabilities(frozenset(PhaseKind), frozenset({"prontera"}), frozenset({"vitals"}))


def test_missing_supplied_receipt_denies_preserving_active_and_attempt_budget() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(IDENTITY, clock, max_attempts=1)
    first = request_from(owner)
    active = decode_plan(plan_arguments(), first, clock.now)
    assert owner.admit(first, active, legacy_caps())
    clock.now = 110.0
    request = request_from(owner)
    proposed = decode_plan(npc_arguments(), request, clock.now)
    assert not owner.admit(request, proposed, legacy_caps())
    assert owner.active == active
    assert owner.version == 1
    assert owner.pending is None
    clock.now = 120.0
    assert owner.request("retry") is None
    assert owner.outcome == "exhausted"
    assert owner.counters["requests"] == 2


def receipt(stage: str = "next", now: float = 100.0) -> NpcObservation:
    return NpcObservation(
        IDENTITY,
        321,
        IDENTITY.session_epoch,
        "prontera",
        1,
        5,
        stage,
        (1, 3, 7) if stage == "menu" else (),
        True,
        now - 1,
        now + 15,
    )


def supplied_caps(stage: str = "next", now: float = 100.0) -> Capabilities:
    return replace(legacy_caps(), npc_observation=receipt(stage, now))


@pytest.mark.parametrize("operation", ["next", "choose"])
@pytest.mark.parametrize("now", [100.0, 1e15])
def test_exact_fresh_receipt_admits_through_real_lifecycle(operation: str, now: float) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: now)
    request = request_from(owner)
    plan = decode_plan(npc_arguments(operation), request, now)
    caps = supplied_caps("next" if operation == "next" else "menu", now)
    assert plan.denial(caps, now) is None
    assert owner.admit(request, plan, caps)
    assert owner.active == plan


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("identity", replace(IDENTITY, character="other")),
        ("npc_id", 322),
        ("npc_id", True),
        ("epoch", 2),
        ("map_name", "izlude"),
        ("opened_sequence", 2),
        ("prompt_sequence", 6),
        ("stage", "menu"),
        ("ready", False),
        ("ready", 1),
        ("observed_at", 101.0),
        ("expires_at", 100.0),
        ("expires_at", float("inf")),
        ("observed_at", float("nan")),
        ("observed_at", 10**400),
        ("expires_at", 10**400),
        ("option_indices", (1,)),
    ],
)
def test_current_receipt_drift_denies_before_and_at_admission(field: str, value: Any) -> None:
    clock = FakeClock()
    owner = PlanLifecycle(IDENTITY, clock)
    request = request_from(owner)
    plan = decode_plan(npc_arguments(), request, clock.now)
    caps = replace(supplied_caps(), npc_observation=replace(receipt(), **{field: value}))
    assert plan.denial(caps, clock.now) is not None
    assert not owner.admit(request, plan, caps)
    assert owner.active is None
    assert owner.counters["rejected"] == 1


@pytest.mark.parametrize("indices", [(1, 7), (True, 3), (3, 3), (3, 255), (), [1, 3]])
def test_choose_requires_exact_valid_received_indices(indices: Any) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    request = request_from(owner)
    plan = decode_plan(npc_arguments("choose"), request, 100.0)
    caps = replace(
        supplied_caps("menu"), npc_observation=replace(receipt("menu"), option_indices=indices)
    )
    assert not owner.admit(request, plan, caps)


def test_receipt_expiry_at_admission_preserves_previous_active_and_budget() -> None:
    clock = FakeClock()
    owner = PlanLifecycle(IDENTITY, clock, max_attempts=1, wait=30)
    first = request_from(owner)
    active = decode_plan(plan_arguments(), first, clock.now)
    assert owner.admit(first, active, legacy_caps())
    clock.now = 110.0
    request = request_from(owner)
    plan = decode_plan(npc_arguments(), request, clock.now)
    caps = supplied_caps(now=clock.now)
    assert plan.denial(caps, clock.now) is None
    clock.now = 125.0
    assert not owner.admit(request, plan, caps)
    assert owner.active == active
    assert owner.version == 1
    clock.now = 140.0
    assert owner.request("retry") is None
    assert owner.outcome == "exhausted"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("operation", "close"),
        ("operation", "name"),
        ("operation", True),
        ("npc_id", 0),
        ("npc_id", 0x100000000),
        ("npc_id", True),
        ("npc_id", "321"),
        ("epoch", -1),
        ("epoch", True),
        ("map_name", "prontera\x00"),
        ("map_name", "x" * 33),
        ("map_name", "Npc::Alias"),
        ("opened_sequence", True),
        ("opened_sequence", 5),
        ("prompt_sequence", 0),
        ("prompt_sequence", 5.0),
        ("expected_stage", "menu"),
        ("option_index", None),
        ("answer", "yes"),
        ("name", "guide"),
        ("command", "next"),
    ],
)
def test_next_decoder_denies_invalid_or_extra_intent_fields(field: str, value: Any) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    args = npc_arguments()
    args["phases"][0]["npc_intent"][field] = value
    with pytest.raises(ValueError, match=r"planning denied|not a valid"):
        decode_plan(args, request_from(owner), 100.0)


@pytest.mark.parametrize("index", [0, 255, True, "3", 3.0, None, "choose guide"])
def test_choose_decoder_denies_cancel_coercion_or_free_text(index: Any) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    args = npc_arguments("choose")
    args["phases"][0]["npc_intent"]["option_index"] = index
    with pytest.raises(ValueError, match=r"planning denied|not a valid"):
        decode_plan(args, request_from(owner), 100.0)


@pytest.mark.parametrize(
    "fault",
    ["multi", "mixed", "success", "progress", "idle-predicate", "epoch", "unknown-fact", "nul"],
)
def test_npc_plan_semantics_deny_unsafe_shape_or_binding(fault: str) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    request = request_from(owner)
    args = npc_arguments()
    if fault in ("multi", "mixed"):
        args["phases"].append(
            args["phases"][0] if fault == "multi" else {"kind": "idle", "map_name": "prontera"}
        )
    elif fault in ("success", "progress"):
        args[fault] = "recovered"
    elif fault == "idle-predicate":
        args["phases"] = [{"kind": "idle", "map_name": "prontera"}]
    elif fault == "epoch":
        args["phases"][0]["npc_intent"]["epoch"] += 1
    elif fault == "unknown-fact":
        args["required_facts"] = ["unknown"]
    else:
        args["objective"] = "read\x00"
    try:
        plan = decode_plan(args, request, 100.0)
    except ValueError:
        return
    assert plan.denial(supplied_caps(), 100.0) is not None
    assert not owner.admit(request, plan, supplied_caps())


@pytest.mark.parametrize(
    "field", ["destination", "public_species", "public_item", "npc_id", "answer"]
)
def test_npc_phase_denies_legacy_targets_or_arbitrary_fields(field: str) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    args = npc_arguments()
    args["phases"][0][field] = [1, 1] if field == "destination" else 321
    with pytest.raises(ValueError, match=r"planning denied|not a valid"):
        decode_plan(args, request_from(owner), 100.0)


def test_non_npc_phase_cannot_carry_typed_intent() -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    args = npc_arguments()
    args["phases"][0]["kind"] = "idle"
    with pytest.raises(ValueError, match=r"planning denied|not a valid"):
        decode_plan(args, request_from(owner), 100.0)


def test_unready_npc_is_not_model_visible_even_when_generic_caps_include_enum() -> None:
    reader, state, sent = fixture_reader()
    caps = legacy_caps()
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, caps)
    model = ScriptedModel(
        [
            frame("investigate", {"topic": "npc"}, "read"),
            frame("submit_plan", plan_arguments(), "plan"),
        ]
    )
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    plan = LlmPlanner(model, reader, lambda: 100.0).propose(request_from(owner), reader)
    assert plan.phases[0].kind is PhaseKind.REST
    for payload in model.payloads:
        advisory = json.loads(payload["messages"][1]["content"])["caller_capabilities"]
        schema = payload["tools"][1]["function"]["parameters"]["properties"]
        assert "npc" not in advisory["supported"]
        assert "npc_observation" not in advisory
        assert "npc" not in schema["phases"]["items"]["properties"]["kind"]["enum"]
        assert "npc ui advanced" not in schema["success"]["enum"]
        assert "npc_intent" not in schema["phases"]["items"]["properties"]
    assert not sent


@pytest.mark.parametrize("operation", ["next", "choose"])
def test_investigation_first_model_gets_exact_binding_then_real_admission(operation: str) -> None:
    reader, state, sent = fixture_reader()
    stage = "next" if operation == "next" else "menu"
    caps = supplied_caps(stage)
    dialogue = NpcDialogue(
        321,
        IDENTITY.session_epoch,
        "prontera",
        1,
        5,
        stage,
        pages=("Received guidance",),
        options=((1, "First"), (3, "Third"), (7, "Seventh")) if stage == "menu" else (),
    )
    state = replace(state, npc_dialogue=dialogue)
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, caps)
    model = ScriptedModel(
        [
            frame("investigate", {"topic": "npc"}, "read"),
            frame("submit_plan", npc_arguments(operation), "plan"),
        ]
    )
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    request = request_from(owner)
    plan = LlmPlanner(model, reader, lambda: 100.0).propose(request, reader)
    assert owner.active is None
    assert owner.admit(request, plan, reader.observed_capabilities(IDENTITY))
    investigation = json.loads(model.payloads[1]["messages"][-1]["content"])
    assert investigation["untrusted_text"] is True
    assert investigation["data"]["dialogue"]["npc_id"] == 321
    assert investigation["data"]["dialogue"]["sequence"] == 5
    assert investigation["data"]["dialogue"]["stage"] == stage
    for payload in model.payloads:
        advisory = json.loads(payload["messages"][1]["content"])["caller_capabilities"]
        assert "npc" in advisory["supported"]
        binding = advisory["npc_observation"]
        assert binding["npc_id"] == 321
        assert binding["prompt_sequence"] == 5
        assert binding["available_operation"] == operation
        assert binding["option_indices"] == ([1, 3, 7] if operation == "choose" else [])
        assert advisory["native_action_authorization"] == "UNKNOWN"
        parameters = payload["tools"][1]["function"]["parameters"]
        variants = parameters["properties"]["phases"]["items"]["anyOf"]
        npc = variants[1]
        assert npc["additionalProperties"] is False
        intent = npc["properties"]["npc_intent"]
        assert intent["additionalProperties"] is False
        assert intent["properties"]["operation"]["enum"] == [operation]
        assert intent["properties"]["npc_id"]["enum"] == [321]
        assert intent["properties"]["prompt_sequence"]["enum"] == [5]
        if operation == "choose":
            assert intent["properties"]["option_index"]["enum"] == [1, 3, 7]
        else:
            assert "option_index" not in intent["properties"]
        assert parameters["allOf"][0]["then"]["properties"]["phases"]["maxItems"] == 1
    assert LlmPlanner.__module__ == "robots.app.llm_planner"
    assert not sent


@pytest.mark.parametrize("field", ["destination", "public_species", "public_item"])
def test_npc_decoder_denies_even_null_legacy_phase_fields(field: str) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    args = npc_arguments()
    args["phases"][0][field] = None
    with pytest.raises(PlanningError, match=r"^planning denied$"):
        decode_plan(args, request_from(owner), 100.0)


def test_invalid_utf8_core_plan_denies_without_escaping_lifecycle() -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    request = request_from(owner)
    plan = replace(decode_plan(npc_arguments(), request, 100.0), objective="\ud800")
    assert not owner.admit(request, plan, supplied_caps())
    assert owner.active is None


@pytest.mark.parametrize(
    "fault", ["duplicate", "extra", "bool", "utf8", "oversized-time", "no-investigation"]
)
def test_malformed_model_submission_denies_without_native_effects(fault: str) -> None:
    reader, state, sent = fixture_reader()
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, supplied_caps())
    args = npc_arguments()
    if fault == "extra":
        args["phases"][0]["npc_intent"]["actor_alias"] = "Guide::Prontera"
    elif fault == "bool":
        args["phases"][0]["npc_intent"]["prompt_sequence"] = True
    elif fault == "utf8":
        args["objective"] = "\ud800"
    elif fault == "oversized-time":
        args["duration"] = 10**400
    response = frame("submit_plan", args, "plan")
    if fault == "duplicate":
        function = response["choices"][0]["message"]["tool_calls"][0]["function"]
        function["arguments"] = function["arguments"].replace(
            '"npc_id": 321', '"npc_id": 321, "npc_id": 321'
        )
    frames = [] if fault == "no-investigation" else [frame("investigate", {"topic": "npc"}, "read")]
    frames.append(response)
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    with pytest.raises(PlanningError, match=r"^planning denied$"):
        LlmPlanner(ScriptedModel(frames), reader, lambda: 100.0).propose(
            request_from(owner), reader
        )
    assert owner.active is None
    assert not sent


@pytest.mark.parametrize(
    "fault", ["missing", "not-ready", "expired", "foreign", "unsupported", "unknown-map"]
)
def test_schema_and_advisory_exclude_ineligible_supplied_receipt(fault: str) -> None:
    caps = supplied_caps()
    if fault == "missing":
        caps = replace(caps, npc_observation=None)
    elif fault == "unsupported":
        caps = replace(caps, supported=frozenset({PhaseKind.IDLE, PhaseKind.REST}))
    elif fault == "unknown-map":
        caps = replace(caps, known_maps=frozenset())
    else:
        changed = {
            "not-ready": replace(receipt(), ready=False),
            "expired": replace(receipt(), expires_at=100.0),
            "foreign": replace(receipt(), identity=replace(IDENTITY, world="foreign")),
        }[fault]
        caps = replace(caps, npc_observation=changed)
    schema = _schemas(caps, IDENTITY, 100.0)[1]["function"]["parameters"]
    assert "allOf" not in schema
    assert "npc" not in schema["properties"]["phases"]["items"]["properties"]["kind"]["enum"]


def test_strict_json_duplicate_nested_keys_and_invalid_utf8_are_denied() -> None:
    duplicate = '{"npc_intent":{"npc_id":321,"npc_id":321}}'
    with pytest.raises(PlanningError, match=r"^planning denied$"):
        strict_json(duplicate)
    with pytest.raises(UnicodeError):
        strict_json("\ud800")


def test_default_receipt_readiness_is_not_automatic() -> None:
    observation = NpcObservation(IDENTITY, 321, 1, "prontera", 1, 5, "next")
    assert observation.ready is False
    assert not observation.eligible(IDENTITY, 100.0)


def test_negative_finite_injected_receipt_clock_has_no_arbitrary_cap() -> None:
    now = -1e15
    request = PlanningRequest("manual", IDENTITY, 0, ("guidance",), now + 30)
    plan = decode_plan(npc_arguments(), request, now)
    assert plan.denial(supplied_caps(now=now), now) is None


def test_final_receipt_read_advancing_clock_denies_expired_model_proposal() -> None:
    reader, state, sent = fixture_reader()
    clock = FakeClock()

    def snapshot() -> ObservationSnapshot:
        if clock.now == 110.0:
            clock.now = 115.0
        return ObservationSnapshot(IDENTITY, state, supplied_caps())

    reader.provider = snapshot

    class AdvancingModel(ScriptedModel):
        def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
            response = super().complete(payload)
            if len(self.payloads) == 2:
                clock.now = 110.0
            return response

    model = AdvancingModel(
        [
            frame("investigate", {"topic": "npc"}, "read"),
            frame("submit_plan", npc_arguments(), "plan"),
        ]
    )
    owner = PlanLifecycle(IDENTITY, clock, wait=30)
    with pytest.raises(PlanningError, match=r"^planning denied$"):
        LlmPlanner(model, reader, clock).propose(request_from(owner), reader)
    assert owner.active is None
    assert not sent


def test_expiring_receipt_schema_and_advisory_share_one_clock_sample() -> None:
    reader, state, sent = fixture_reader()
    caps = replace(supplied_caps(), npc_observation=replace(receipt(), expires_at=104.0))
    reader.provider = lambda: ObservationSnapshot(IDENTITY, state, caps)
    clock = FakeClock()

    def advancing_clock() -> float:
        clock.now += 1
        return clock.now

    class ConsistentModel(ScriptedModel):
        def complete(self, payload: dict[str, Any]) -> dict[str, Any]:
            advisory = json.loads(payload["messages"][1]["content"])["caller_capabilities"]
            properties = payload["tools"][1]["function"]["parameters"]["properties"]
            has_npc_schema = "anyOf" in properties["phases"]["items"]
            assert has_npc_schema == ("npc" in advisory["supported"])
            return super().complete(payload)

    model = ConsistentModel(
        [
            frame("investigate", {"topic": "npc"}, "read"),
            frame("submit_plan", plan_arguments(), "plan"),
        ]
    )
    request = PlanningRequest("manual", IDENTITY, 0, ("guidance",), 200.0)
    plan = LlmPlanner(model, reader, advancing_clock).propose(request, reader)
    assert plan.phases[0].kind is PhaseKind.REST
    assert not sent


@pytest.mark.parametrize(("field", "value"), [("option_indices", None), ("map_name", ["prontera"])])
def test_malformed_typed_receipt_denies_before_schema_or_lifecycle(field: str, value: Any) -> None:
    owner = PlanLifecycle(IDENTITY, lambda: 100.0)
    request = request_from(owner)
    plan = decode_plan(npc_arguments("choose"), request, 100.0)
    observation = replace(receipt("menu"), **{field: value})
    caps = replace(supplied_caps("menu"), npc_observation=observation)
    assert not owner.admit(request, plan, caps)
    schema = _schemas(caps, IDENTITY, 100.0)[1]["function"]["parameters"]
    assert "allOf" not in schema
