"""Received NPC entry names must reach owner-local perceived state."""

import struct

import pytest

from robots.adapters.native_actor_presentation import actor_entry_npc_name
from robots.adapters.native_vitals import NativeTelemetryUnavailable
from robots.app.playing_runtime import PlayingClient
from robots.domain.model import Goal
from tests.test_playing_runtime import Wire, position


def test_received_actor_entry_retains_npc_name() -> None:
    wire = Wire()
    wire.frames = []
    wire.map_name = "prt_fild08"
    auth = b"\xeb\x02" + bytes(4) + position(176, 374) + bytes(4)
    entry = bytearray(103)
    struct.pack_into("<HHBII", entry, 0, 0x09FE, 103, 6, 444, 0)
    entry[59:62] = position(175, 374)
    entry[79:103] = b"Bard#brising".ljust(24, b"\0")
    wire.add(auth, bytes(entry))
    client = PlayingClient(wire)

    state = client.build_native_state(Goal.GRIND)

    assert state.nearby[0].name == "Bard#brising"
    assert wire.sent == []


def actor_entry(
    pid: int = 0x09FE, kind: int = 6, name: bytes = b"Bard#brising", aid: int = 444
) -> bytes:
    """Synthetic pinned layout: name is the last NAME_LENGTH=24 bytes."""
    size = {0x09FD: 110, 0x09FE: 103, 0x09FF: 104}[pid]
    raw = bytearray(size)
    struct.pack_into("<HHBII", raw, 0, pid, size, kind, aid, 0)
    offset = 63 if pid == 0x09FD else 59
    raw[offset : offset + 3] = position(175, 374)
    raw[-24:] = name.ljust(24, b"\0")
    return bytes(raw)


def received_client(*frames: bytes) -> tuple[PlayingClient, Wire]:
    wire = Wire()
    wire.frames = []
    wire.map_name = "prt_fild08"
    wire.add(b"\xeb\x02" + bytes(4) + position(176, 374) + bytes(4), *frames)
    return PlayingClient(wire), wire


@pytest.mark.parametrize("name", [b"", b"\xff"])
def test_new_entry_with_unknown_name_clears_previous_received_name(name: bytes) -> None:
    client, wire = received_client(actor_entry())
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "Bard#brising"
    wire.add(actor_entry(name=name))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#444"
    assert wire.sent == []


@pytest.mark.parametrize("pid", [0x09FD, 0x09FE, 0x09FF])
@pytest.mark.parametrize("kind", [6, 12])
def test_received_name_all_pinned_npc_presentations(pid: int, kind: int) -> None:
    client, wire = received_client(actor_entry(pid, kind))
    state = client.build_native_state(Goal.GRIND)
    assert (state.nearby[0].id, state.nearby[0].name, state.nearby[0].kind) == (
        444,
        "Bard#brising",
        "npc",
    )
    assert state.nearby_monsters == ()
    assert client._tracker is not None
    assert client._tracker.view.actors[0].walking is (pid == 0x09FD)
    assert wire.sent == []


@pytest.mark.parametrize("kind", [0, 5, 255])
def test_foreign_presentation_does_not_retain_npc_name(kind: int) -> None:
    client, wire = received_client(actor_entry(kind=kind))
    state = client.build_native_state(Goal.GRIND)
    assert actor_entry_npc_name(actor_entry(kind=kind)) is None
    assert client._npc_names == {}
    assert not any(actor.kind == "npc" for actor in state.nearby)
    assert wire.sent == []


@pytest.mark.parametrize("name", [b"", b"\xff", b"\xf0\x9f"])
def test_invalid_entry_name_remains_unknown(name: bytes) -> None:
    client, wire = received_client(actor_entry(name=name))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#444"
    assert wire.sent == []


@pytest.mark.parametrize("name", [b"x" * 24, "Bárd".encode(), b"Bard\0ignored", b"Bard\n"])
def test_entry_name_preserves_existing_reply_text_policy(name: bytes) -> None:
    client, wire = received_client(actor_entry(name=name))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == name.split(b"\0")[0].decode()
    assert wire.sent == []


@pytest.mark.parametrize("fault", ["short", "long", "declared", "foreign", "mutable"])
def test_malformed_profile_entry_rejected(fault: str) -> None:
    raw = actor_entry()
    malformed_cases: dict[str, bytes | bytearray] = {
        "short": raw[:-1],
        "long": raw + b"\0",
        "declared": raw[:2] + b"\x68\0" + raw[4:],
        "foreign": b"\xfe\x08" + raw[2:],
        "mutable": bytearray(raw),
    }
    with pytest.raises(ValueError, match="Invalid native actor presentation frame"):
        actor_entry_npc_name(malformed_cases[fault])  # type: ignore[arg-type]


@pytest.mark.parametrize("fault", ["short", "declared", "packet_id", "gap"])
def test_bad_received_frame_denies_state_before_name_projection(fault: str) -> None:
    client, wire = received_client(actor_entry())
    client.build_native_state(Goal.GRIND)
    raw = actor_entry(name=b"New")
    seq, at, pid = 3, 3.0, 0x09FE
    if fault == "short":
        raw = raw[:-1]
    elif fault == "declared":
        raw = raw[:2] + b"\x68\0" + raw[4:]
    elif fault == "packet_id":
        pid = 0x09FF
    else:
        seq = 4
    wire.frames.append((seq, at, pid, raw))
    with pytest.raises(NativeTelemetryUnavailable):
        client.build_native_state(Goal.GRIND)
    assert wire.sent == []


def name_reply(name: bytes = b"Reply", aid: int = 444) -> bytes:
    return struct.pack("<HII24s24s", 0x0ADF, aid, 0, name, b"")


def test_received_reply_overrides_entry_until_new_entry() -> None:
    client, wire = received_client(actor_entry(), name_reply())
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "Reply"
    wire.add(actor_entry(name=b"New"))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "New"
    wire.add(name_reply(b"\xff"))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "New"
    assert wire.sent == []


def test_reply_before_actor_is_not_a_hidden_registry() -> None:
    client, wire = received_client(name_reply(), actor_entry(name=b""))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#444"
    assert wire.sent == []


@pytest.mark.parametrize("boundary", ["vanish", "map", "epoch"])
def test_received_boundary_forgets_name_before_same_id_reentry(boundary: str) -> None:
    client, wire = received_client(actor_entry())
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "Bard#brising"
    if boundary == "vanish":
        wire.add(struct.pack("<HIB", 0x0080, 444, 0), name_reply())
    elif boundary == "map":
        wire.add(struct.pack("<H16sHH", 0x0091, b"prt_fild08", 176, 374), name_reply())
    else:
        wire.native_epoch = wire.selection_epoch = wire.map_epoch = 2
        wire.frames = []
        wire.add(b"\xeb\x02" + bytes(4) + position(176, 374) + bytes(4), name_reply())
    wire.add(actor_entry(name=b""))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#444"
    assert wire.sent == []


def test_names_are_client_local_even_with_repeated_actor_ids() -> None:
    first, wire = received_client(actor_entry())
    second, other = received_client(actor_entry(name=b"Other"))
    assert first.build_native_state(Goal.GRIND).nearby[0].name == "Bard#brising"
    assert second.build_native_state(Goal.GRIND).nearby[0].name == "Other"
    assert wire.sent == other.sent == []


def test_actor_zero_cannot_acquire_retained_npc_name() -> None:
    client, wire = received_client(actor_entry(aid=0))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#0"
    assert client._npc_names == {}
    assert wire.sent == []


def test_entry_without_perceived_actor_cannot_install_name() -> None:
    client, wire = received_client()
    client.build_native_state(Goal.GRIND)
    client._receive_actor_entry_name(actor_entry())
    assert client._npc_names == {}
    assert wire.sent == []


def test_replacing_wire_session_does_not_reuse_names() -> None:
    client, first = received_client(actor_entry())
    client.build_native_state(Goal.GRIND)
    _, second = received_client(actor_entry(name=b""))
    client.wire = second
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "NPC#444"
    assert first.sent == second.sent == []


def test_duplicate_received_sequence_does_not_replace_name() -> None:
    client, wire = received_client(actor_entry())
    client.build_native_state(Goal.GRIND)
    wire.frames.append((2, 2.0, 0x09FE, actor_entry(name=b"Replayed")))
    assert client.build_native_state(Goal.GRIND).nearby[0].name == "Bard#brising"
    assert wire.sent == []
