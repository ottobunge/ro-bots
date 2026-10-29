"""Synthetic source-shaped received skill context; no network or inference."""

import json
import struct
from collections import deque
from types import SimpleNamespace
from typing import Any

import pytest

from robots.adapters.native_progression import SelectedCharacterSnapshot
from robots.adapters.native_skills import NativeSkillContext, decode_skills
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.decisions import build_decision_request
from robots.domain.model import BotState, Goal
from robots.domain.skills import EffectiveSkill, ReceivedSkillContextReadOnly
from tests.test_client_protocol import FakeSocket
from tests.test_client_protocol import client as native
from tests.test_native_npc_close_framing import packet_module
from tests.test_playing_runtime import entry, monster


def skills(playing: PlayingClient) -> Any:
    context = playing.build_native_state(Goal.GRIND).received_skills
    assert context is not None
    return context


def row(skill_id: int = 1, level: int = 9, flag: int = 0) -> bytes:
    return struct.pack("<HiHHH24sB", skill_id, -1, level, 0, 1, b"NV_BASIC", flag)


def skill_list(*rows: bytes) -> bytes:
    body = b"".join(rows)
    return struct.pack("<hh", 0x010F, len(body) + 4) + body


def setup() -> tuple[Any, PlayingClient, list[bytes]]:
    bot = native.BotClient("offline", "not_a_credential", verbose=False)
    bot.aid, bot.gid, bot.char_name = 999, 77, "WireNovice"
    bot.native_epoch = bot.selection_epoch = bot.map_epoch = 1
    bot.class_fresh = True
    bot.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 10, 10, 0, 0)
    bot.running = bot.connected_map = True
    bot.sock = object()
    bot.rx_thread = SimpleNamespace(is_alive=lambda: True)
    bot.map_name = "prontera"
    sent: list[bytes] = []
    bot._send = sent.append
    dispatch(bot, entry() + monster())
    for param, value in ((5, 100), (6, 100), (7, 0), (8, 20), (12, 0)):
        dispatch(bot, struct.pack("<HHi", 0x00B0, param, value))
    return bot, PlayingClient(bot), sent


def dispatch(bot: Any, stream: bytes) -> None:
    packets, remaining = packet_module().parse_stream(stream)
    assert not remaining
    for pid, raw in packets:
        bot._dispatch(pid, raw)


def test_received_basic9_and_zero_tree_row_reach_clef_with_zero_free_points() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row(), row(2, 0, 1)))
    state = playing.build_native_state(Goal.GRIND)
    facts = build_decision_request(state)["state"].get("observed_effective_skills")
    assert facts is not None, "received skill rows must reach actual Clef state"
    assert [(r["id"], r["level"]) for r in facts["rows"]] == [(1, 9), (2, 0)]
    assert facts["complete"] == "UNKNOWN"
    assert facts["status"] == "PARTIAL"
    assert facts["ownership"] == "UNKNOWN"
    assert not sent


def test_ordered_partial_updates_keep_lower_levels_and_unknown_fields() -> None:
    bot, playing, sent = setup()
    packets = [
        skill_list(row()),
        struct.pack("<HHHHHB", 0x010E, 1, 0, 2, 3, 255),
        struct.pack("<HHiHHHB", 0x07E1, 2, -2147483648, 4, 5, 6, 2),
        struct.pack("<HHHHHB", 0x010E, 3, 7, 8, 9, 1),
    ]
    dispatch(bot, b"".join(packets))
    facts = build_decision_request(playing.build_native_state(Goal.GRIND))["state"][
        "observed_effective_skills"
    ]
    assert facts["status"] == "PARTIAL"
    assert [(r["id"], r["level"], r["inf"], r["up_flag_raw"]) for r in facts["rows"]] == [
        (1, 0, -1, 255),
        (2, 4, -2147483648, 2),
        (3, 7, None, 1),
    ]
    assert not sent


def test_collector_invalid_packet_metadata_clears_received_rows() -> None:
    collector = NativeSkillContext(1, 0)
    collector.consume((1, 1.0, 0x010F, skill_list(row())))
    assert collector.context.rows
    collector.consume((2, 2.0, True, skill_list(row())))
    assert collector.context.decision_facts()["status"] == "UNKNOWN"


def test_received_rows_require_session_provenance() -> None:
    with pytest.raises(ValueError, match="skill"):
        ReceivedSkillContextReadOnly((EffectiveSkill(1, 9, 0, 1, 0),))


def test_collector_rejects_boolean_timestamp() -> None:
    collector = NativeSkillContext(1, 0)
    collector.consume((1, True, 0x010F, skill_list(row())))
    assert collector.context.decision_facts()["status"] == "UNKNOWN"


def test_stream_all_families_fragmented_and_coalesced() -> None:
    module = packet_module()
    packets = [
        skill_list(row()),
        struct.pack("<H", 0x0111) + row(2, 0),
        struct.pack("<HHHHHB", 0x010E, 1, 0, 0, 0, 1),
        struct.pack("<HHiHHHB", 0x07E1, 2, -1, 4, 5, 6, 255),
    ]
    expected = [(int.from_bytes(p[:2], "little"), p) for p in packets]
    assert module.parse_stream(b"".join(packets)) == (expected, b"")
    pending = b""
    observed = []
    for byte in b"".join(packets):
        ready, pending = module.parse_stream(pending + bytes([byte]))
        observed.extend(ready)
    assert observed == expected
    assert not pending
    # 901 prior registrations + the guild-create reply 0x0167 (charter slice)
    # + the wear-equip ack 0x0999 and the guild login notice 0x01F2 (leg 35).
    assert len(module.PACKET_DB) == 909


def test_empty_list_only_empty_receipt_then_partner_add() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list())
    facts = build_decision_request(playing.build_native_state(Goal.GRIND))["state"][
        "observed_effective_skills"
    ]
    assert facts["status"] == "PARTIAL"
    assert facts["complete"] == "UNKNOWN"
    assert facts["rows"] == []
    dispatch(bot, struct.pack("<H", 0x0111) + row(336, 1))
    state = playing.build_native_state(Goal.GRIND)
    assert state.received_skills is not None
    assert [(r.id, r.level) for r in state.received_skills.rows or ()] == [(336, 1)]
    assert not sent


def test_skill_frames_do_not_rewrite_unrelated_clef_state() -> None:
    bot, playing, sent = setup()
    before = build_decision_request(playing.build_native_state(Goal.GRIND), ["memory"])
    dispatch(bot, skill_list(row()))
    after = build_decision_request(playing.build_native_state(Goal.GRIND), ["memory"])
    before["state"].pop("observed_effective_skills")
    after["state"].pop("observed_effective_skills")
    assert before == after
    assert not sent


def test_display_budget_and_retention_overflow_are_distinct() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(*(row(i) for i in range(1, 222))))
    facts = build_decision_request(playing.build_native_state(Goal.GRIND))["state"][
        "observed_effective_skills"
    ]
    assert facts["observed_count"] == 221
    assert facts["truncated"] is True
    assert len(facts["rows"]) == 8
    assert len(json.dumps(facts, ensure_ascii=False, separators=(",", ":")).encode()) <= 2048
    for i in range(222, 258):
        dispatch(bot, struct.pack("<H", 0x0111) + row(i))
    assert skills(playing).rows is None
    dispatch(bot, skill_list())
    assert skills(playing).rows is None
    assert not sent


def test_all_upgrade_bytes_remain_opaque() -> None:
    for flag in range(256):
        fact = decode_skills(0x0111, struct.pack("<H", 0x0111) + row(flag=flag))[0]
        assert fact.skill.up_flag_raw == flag
        assert fact.skill.level == 9


def test_malformed_duplicate_rows_poison_and_cannot_replay() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row(), row()))
    assert skills(playing).rows is None
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows is None
    assert not sent


def test_transport_failure_clears_context_without_stale_revival() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    bot.running = False
    with pytest.raises(NativeTelemetryUnavailable):
        playing.build_native_state(Goal.GRIND)
    assert playing.received_skills.rows is None
    bot.running = True
    assert skills(playing).rows is None
    assert not sent


@pytest.mark.parametrize(
    "raw",
    [b"\x0f\x01", skill_list(row(0)), skill_list(row())[:-1], struct.pack("<H", 0x010E), bytes(39)],
)
def test_decoder_malformed_receipts_fail_closed(raw: bytes) -> None:
    with pytest.raises(ValueError, match="skill"):
        decode_skills(int.from_bytes(raw[:2], "little"), raw)


def test_session_collector_gap_and_delete_poison() -> None:
    collector = NativeSkillContext(1, 0)
    collector.consume((1, 1.0, 0x010F, skill_list(row())))
    assert collector.context.rows
    collector.consume((3, 3.0, 0x010F, skill_list()))
    assert collector.context.decision_facts()["status"] == "UNKNOWN"
    collector.consume((2, 2.0, 0x010F, skill_list(row())))
    assert collector.context.decision_facts()["status"] == "UNKNOWN"
    fresh = NativeSkillContext(2, 0)
    fresh.consume((1, 1.0, 0x010F, skill_list(row())))
    fresh.consume((2, 2.0, 0x0441, struct.pack("<HH", 0x0441, 1)))
    assert fresh.context.rows is None


def test_class_invalidation_clears_skill_context() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    playing.build_native_state(Goal.GRIND)
    bot.class_fresh = False
    with pytest.raises(NativeTelemetryUnavailable):
        playing.build_native_state(Goal.GRIND)
    assert playing.received_skills.rows is None
    assert not sent


@pytest.mark.parametrize(("pid", "size"), [(0x0091, 22), (0x0092, 28), (0x0AC7, 156)])
def test_real_map_receipt_invalidates_previously_projected_skills(pid: int, size: int) -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row(), row(2, 0)))
    assert [(r.id, r.level) for r in skills(playing).rows] == [(1, 9), (2, 0)]
    packet = struct.pack("<H16sHH", pid, b"prontera", 50, 50) + bytes(size - 22)
    dispatch(bot, packet)
    if pid == 0x0091:
        state = playing.build_native_state(Goal.GRIND)
        assert (state.x, state.y) == (50, 50)
        assert state.received_skills is not None
        assert state.received_skills.rows is None
        # Existing LoadEndAck is real offline dispatch output, not skill actuation.
        assert sent == [b"\x7d\x00"]
        dispatch(bot, skill_list(row(3, 0)))
        assert [(r.id, r.level) for r in skills(playing).rows] == [(3, 0)]
    else:
        with pytest.raises(NativeTelemetryUnavailable):
            playing.build_native_state(Goal.GRIND)
        assert playing.received_skills.rows is None
        assert not sent


def test_real_retained_frame_eviction_reaches_tracker_gap() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    # Evict an unconsumed frame in the actual BotClient receive ring.
    bot._native_frames = deque(bot._native_frames, maxlen=2)
    for value in (1, 2, 3):
        dispatch(bot, struct.pack("<HHi", 0x00B0, 12, value))
    with pytest.raises(NativeTelemetryUnavailable, match="continuity"):
        playing.build_native_state(Goal.GRIND)
    assert playing.received_skills.rows is None
    dispatch(bot, skill_list(row()))
    with pytest.raises(NativeTelemetryUnavailable, match="continuity"):
        playing.build_native_state(Goal.GRIND)
    assert playing.received_skills.rows is None
    assert not sent


def test_distinct_real_client_equal_epoch_sequence_cannot_share_skills() -> None:
    old, playing, sent = setup()
    dispatch(old, skill_list(row()))
    assert skills(playing).rows[0].id == 1
    new, _, new_sent = setup()
    new.char_name = "OtherWireNovice"
    dispatch(new, skill_list(row(2, 0)))
    assert old is not new
    assert old.native_frame_snapshot()[:2] == new.native_frame_snapshot()[:2]
    assert old.native_frame_snapshot()[2][-1][0] == new.native_frame_snapshot()[2][-1][0]
    playing.wire = new
    state = playing.build_native_state(Goal.GRIND)
    assert state.name == "OtherWireNovice"
    assert state.received_skills is not None
    assert state.received_skills.rows is not None
    assert [(r.id, r.level) for r in state.received_skills.rows] == [(2, 0)]
    assert not sent
    assert not new_sent


def test_actual_close_clears_received_skills_and_selected_snapshot() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    sock = FakeSocket()
    bot.sock = sock
    bot.rx_thread = SimpleNamespace(is_alive=lambda: False)
    playing.close()
    assert sock.closed
    assert sock.shutdown_called
    assert bot.selected_character_snapshot is None
    assert bot.map_epoch is None
    assert playing.received_skills.rows is None
    with pytest.raises(NativeTelemetryUnavailable):
        playing.build_native_state(Goal.GRIND)
    assert not sent


def test_actual_connect_lifecycle_without_network_replaces_epoch_evidence(monkeypatch: Any) -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    old_epoch, _, old_frames = bot.native_frame_snapshot()
    bot.sock = FakeSocket()
    bot.rx_thread = SimpleNamespace(is_alive=lambda: False)

    def login() -> tuple[str, int]:
        assert playing.received_skills.rows is None
        assert bot.selected_character_snapshot is None
        assert bot.selection_epoch is None
        assert bot.map_epoch is None
        assert bot.native_frame_snapshot()[2] == ()
        return "offline", 1

    def select(_ip: str, _port: int) -> tuple[str, int]:
        bot.selected_character_snapshot = SelectedCharacterSnapshot(77, 0, 10, 10, 0, 0)
        bot.selection_epoch = bot.native_epoch
        bot.class_fresh = True
        return "offline", 1

    def map_transport(_ip: str, _port: int) -> None:
        bot.sock = FakeSocket()
        bot.map_epoch = bot.native_epoch
        bot.running = bot.connected_map = True
        bot.rx_thread = SimpleNamespace(is_alive=lambda: True)
        dispatch(bot, entry())
        for param, value in ((5, 100), (6, 100), (7, 0), (8, 20), (12, 0)):
            dispatch(bot, struct.pack("<HHi", 0x00B0, param, value))

    monkeypatch.setattr(bot, "_login_server", login)
    monkeypatch.setattr(bot, "_char_server", select)
    monkeypatch.setattr(bot, "_map_server", map_transport)
    # Real BotClient.connect/close/reset; only transport handshake seams are offline.
    assert playing.connect() is bot
    assert bot.native_epoch == old_epoch + 1
    assert skills(playing).rows is None
    bot._native_frames.append(old_frames[-1])
    assert skills(playing).rows is None  # stale old-session sequence cannot attach rows
    bot._native_frames.pop()
    dispatch(bot, skill_list(row(2, 0)))
    context = skills(playing)
    assert context.epoch == old_epoch + 1
    assert [(r.id, r.level) for r in context.rows] == [(2, 0)]
    assert not sent


def test_receive_error_recovery_does_not_replay_prior_skill_frames() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    bot.rx_error = OSError("offline transport fault")
    with pytest.raises(NativeTelemetryUnavailable):
        playing.build_native_state(Goal.GRIND)
    assert playing.received_skills.rows is None
    bot.rx_error = None
    dispatch(bot, skill_list(row(2, 0)))
    assert skills(playing).rows is None
    assert not sent


def test_delete_through_real_wrapper_blocks_until_new_session() -> None:
    bot, playing, sent = setup()
    dispatch(bot, skill_list(row()))
    assert skills(playing).rows
    dispatch(bot, struct.pack("<HH", 0x0441, 1))
    assert skills(playing).rows is None
    dispatch(bot, skill_list(row(2, 0)))
    assert skills(playing).rows is None
    assert not sent


@pytest.mark.parametrize("field", ["id", "level", "sp", "range", "up_flag_raw", "inf"])
def test_effective_skill_public_integer_boundaries_reject_boolean(field: str) -> None:
    values = {"id": 1, "level": 0, "sp": 0, "range": 0, "up_flag_raw": 0, "inf": 0}
    values[field] = True
    with pytest.raises(ValueError, match="skill"):
        EffectiveSkill(**values)


def test_context_and_collector_boolean_session_metadata_are_denied() -> None:
    for epoch, sequence in ((True, 0), (1, True)):
        with pytest.raises(ValueError, match="skill"):
            ReceivedSkillContextReadOnly(epoch=epoch, sequence=sequence)
        with pytest.raises(ValueError, match="skill"):
            NativeSkillContext(epoch, sequence)


def test_context_malformed_rows_and_incomplete_provenance_are_denied() -> None:
    skill = EffectiveSkill(1, 0, 0, 0, 0)
    for rows in ([skill], (None,), (skill, skill), (skill,) * 257):
        with pytest.raises(ValueError, match="skill"):
            ReceivedSkillContextReadOnly(rows, 1, 0)  # type: ignore[arg-type]
    for epoch, sequence in ((None, 0), (1, None)):
        with pytest.raises(ValueError, match="skill"):
            ReceivedSkillContextReadOnly((skill,), epoch, sequence)


def test_decoder_public_packet_and_byte_types_are_strict() -> None:
    raw = skill_list(row())
    for pid, packet in ((True, raw), (0x010F, bytearray(raw)), (0x010F, memoryview(raw))):
        with pytest.raises(ValueError, match="skill"):
            decode_skills(pid, packet)  # type: ignore[arg-type]


def test_collector_invalid_time_and_sequence_clear_known_rows() -> None:
    for seq, at in ((True, 2.0), (2, True), (2, float("nan")), (2, float("inf"))):
        collector = NativeSkillContext(1, 0)
        collector.consume((1, 1.0, 0x010F, skill_list(row())))
        assert collector.context.rows
        collector.consume((seq, at, 0x010F, skill_list(row())))
        assert collector.context.rows is None


def test_worst_case_numeric_skill_payload_and_explicit_bounds() -> None:
    rows = tuple(EffectiveSkill(65535 - i, 65535, 65535, 65535, 255, -(2**31)) for i in range(8))
    facts = ReceivedSkillContextReadOnly(rows, 2**63 - 1, 2**63 - 1).decision_facts()
    payload = json.dumps(facts, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert len(payload) <= 2048
    assert len(facts["rows"]) == 8
    assert facts["truncated"] is False
    assert EffectiveSkill(1, 0, 0, 0, 0, 2**31 - 1).level == 0
    for values in ((0, 0, 0, 0, 0), (65536, 0, 0, 0, 0), (1, -1, 0, 0, 0), (1, 65536, 0, 0, 0)):
        with pytest.raises(ValueError, match="skill"):
            EffectiveSkill(*values)


def test_legacy_botstate_defaults_to_unknown_without_native_epoch() -> None:
    state = BotState(
        "Legacy", "Novice", 1, 1, 1, 0, 0, "prontera", 1, 1, Goal.GRIND, False, (), {}, (), ()
    )
    assert state.received_skills is None
    assert state.native_epoch is None
    facts = build_decision_request(state)["state"]["observed_effective_skills"]
    assert facts["status"] == "UNKNOWN"
    assert facts["rows"] == []
    assert facts["epoch"] is None
    assert facts["sequence"] is None
