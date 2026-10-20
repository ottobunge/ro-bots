"""Source-shaped offline selection receipts, never current class authority."""

import importlib.util
import struct
from collections import deque
from pathlib import Path
from typing import Any

import pytest

from robots.adapters.native_progression import SelectedCharacterSnapshot

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "native_progression_client", ROOT / "spikes/003-clientless-limbs/client.py"
)
assert SPEC is not None
assert SPEC.loader is not None
client = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(client)


def row(cid: int, name: str, slot: int, job: int, base: int, *, level: int = 4) -> bytes:
    raw = bytearray(155)
    struct.pack_into("<I", raw, 0, cid)
    struct.pack_into("<i", raw, 24, level)
    struct.pack_into("<h", raw, 64, job)
    struct.pack_into("<h", raw, 72, base)
    raw[88:112] = name.encode().ljust(24, b"\0")
    raw[118] = slot
    raw[154] = 1
    return bytes(raw)


def characters(*rows: bytes) -> bytes:
    return struct.pack("<HHBBB20s", 0x006B, 27 + len(b"".join(rows)), 9, 9, 9, b"") + b"".join(rows)


def zone(pid: int = 0x0AC5, cid: int = 202) -> bytes:
    raw = bytearray(156 if pid == 0x0AC5 else 28)
    struct.pack_into("<HI", raw, 0, pid, cid)
    raw[6:22] = b"test_map".ljust(16, b"\0")
    raw[22:26] = bytes([127, 0, 0, 1])
    struct.pack_into("<H", raw, 26, 5121)
    return bytes(raw)


class Wire:
    def __init__(self, frames: bytes) -> None:
        self.chunks = deque([struct.pack("<I", 11), frames])
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, _value: float) -> None:
        pass

    def recv(self, count: int) -> bytes:
        if not self.chunks:
            return b""
        raw = self.chunks.popleft()
        if len(raw) > count:
            self.chunks.appendleft(raw[count:])
        return raw[:count]

    def sendall(self, raw: bytes) -> None:
        self.sent.append(raw)

    def __exit__(self, *_args: object) -> None:
        self.closed = True


def setup(monkeypatch: pytest.MonkeyPatch, rows: bytes, route: bytes) -> tuple[Any, Wire]:
    wire = Wire(rows + struct.pack("<HIIH", 0x08B9, 0, 11, 0) + route)
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_kw: wire)
    bot = client.BotClient("offline", "not_a_credential", char_name="Selected", verbose=False)
    bot.aid = 11
    return bot, wire


def test_selected_second_row_uses_wire_slot_and_retains_only_its_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot, wire = setup(
        monkeypatch,
        characters(row(101, "Other", 3, 1, 90, level=40), row(202, "Selected", 7, 0, 8)),
        zone(),
    )
    assert bot._char_server("127.0.0.1", 6121) == ("127.0.0.1", 5121)
    assert wire.sent[-1] == struct.pack("<HB", 0x0066, 7)
    assert bot.gid == 202
    assert bot.selected_character_snapshot == SelectedCharacterSnapshot(202, 0, 8, 4, 7, 1)
    assert bot.status_params == {}
    assert wire.closed


@pytest.mark.parametrize("pid", [0x0AC5, 0x0071])
@pytest.mark.parametrize("cid", [0, 101, 203])
def test_route_mismatch_rejects_before_publishing_or_installing_map(
    monkeypatch: pytest.MonkeyPatch, pid: int, cid: int
) -> None:
    bot, wire = setup(monkeypatch, characters(row(202, "Selected", 7, 0, 8)), zone(pid, cid))
    bot.map_name = "old_map"
    with pytest.raises(RuntimeError, match=r"^selected character route mismatch$"):
        bot._char_server("127.0.0.1", 6121)
    assert bot.selected_character_snapshot is None
    assert bot.map_name == "old_map"
    assert bot.gid == 202
    assert wire.sent == [
        struct.pack("<HIIIHB", 0x0065, 11, 0, 0, 0, 1),
        struct.pack("<HB", 0x0066, 7),
    ]
    assert wire.closed


@pytest.mark.parametrize("parameter", [11, 55])
@pytest.mark.parametrize("value", [12, 1, 0, -1, -(2**31), 2**31 - 1])
def test_self_levels_are_retained_as_exact_signed_receipts(parameter: int, value: int) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    for count in (99, value):
        raw = struct.pack("<HHi", 0x00B0, parameter, count)
        packets, rest = client.pdb.parse_stream(raw)
        assert rest == b""
        for pid, packet in packets:
            bot._dispatch(pid, packet)
    assert bot.status_params == {parameter: value}


@pytest.mark.parametrize("kind", ["cid", "slot", "name", "partial"])
def test_invalid_list_rejects_entire_candidate_before_selection(
    monkeypatch: pytest.MonkeyPatch, kind: str
) -> None:
    other = row(101, "Other", 3, 1, 90, level=40)
    selected = row(202, "Selected", 7, 0, 8)
    if kind == "cid":
        other = row(202, "Other", 3, 1, 90, level=40)
    elif kind == "slot":
        other = row(101, "Other", 7, 1, 90, level=40)
    elif kind == "name":
        other = row(101, "Selected", 3, 1, 90, level=40)
    else:
        other = other[:-1]
    bot, wire = setup(monkeypatch, characters(selected, other), zone())
    with pytest.raises(ValueError, match=r"^malformed native character list$"):
        bot._char_server("127.0.0.1", 6121)
    assert bot.selected_character_snapshot is None
    assert len(wire.sent) == 1


@pytest.mark.parametrize("boundary", ["char", "connect", "close"])
def test_selection_is_cleared_before_fallible_lifecycle(
    monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    assert bot.selected_character_snapshot is None
    bot.selected_character_snapshot = SelectedCharacterSnapshot(202, 0, 8, 4, 7, 1)
    origin = OSError("offline failure")

    def fail(*_args: object, **_kwargs: object) -> Any:
        assert bot.selected_character_snapshot is None
        raise origin

    if boundary == "char":
        monkeypatch.setattr(client.socket, "create_connection", fail)
        with pytest.raises(OSError, match="offline") as caught:
            bot._char_server("127.0.0.1", 6121)
    elif boundary == "connect":
        monkeypatch.setattr(bot, "close", fail)
        with pytest.raises(OSError, match="offline") as caught:
            bot.connect()
    else:
        monkeypatch.setattr(bot, "_release_handshake_socket", fail)
        bot._temporary_sockets.append(object())
        with pytest.raises(RuntimeError, match="temporary socket cleanup failed") as cleanup:
            bot.close()
        assert cleanup.value.__cause__ is origin
        return
    assert caught.value is origin


@pytest.mark.parametrize("job", [0, 1, -1, 4001, 32767])
@pytest.mark.parametrize("pid", [0x0AC5, 0x0071])
def test_raw_job_is_provenance_not_classification(
    monkeypatch: pytest.MonkeyPatch, job: int, pid: int
) -> None:
    bot, _wire = setup(
        monkeypatch, characters(row(202, "Selected", 7, job, -2, level=-3)), zone(pid)
    )
    bot._char_server("127.0.0.1", 6121)
    assert bot.selected_character_snapshot == SelectedCharacterSnapshot(202, job, -2, -3, 7, 1)
    assert bot.status_params == {}
    assert not hasattr(bot, "job_fresh")
    assert not hasattr(bot, "native_progression")


@pytest.mark.parametrize("damage", ["header", "length", "short", "bytearray", "tail"])
def test_list_frame_contract_rejects_before_decoding(damage: str) -> None:
    raw: Any = characters(row(202, "Selected", 7, 0, 8))
    if damage == "header":
        raw = b"\x6c\x00" + raw[2:]
    elif damage == "length":
        raw = raw[:2] + b"\x04\x00" + raw[4:]
    elif damage == "short":
        raw = raw[:26]
    elif damage == "bytearray":
        raw = bytearray(raw)
    else:
        raw += b"x"
    with pytest.raises(ValueError, match=r"^malformed native character list$"):
        client.BotClient._decode_character_list(raw)


@pytest.mark.parametrize(
    "raw", [b"\xb0\x00", struct.pack("<HHi", 0x00B1, 11, 88), b"\xb0\x00" + bytes(7)]
)
def test_malformed_status_preserves_received_levels(raw: bytes) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 11, 7))
    with pytest.raises(ValueError, match=r"^malformed native status packet$"):
        bot._dispatch(0x00B0, raw)
    assert bot.status_params == {11: 7}


def test_counters_and_class_enum_cannot_replace_levels() -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    raw = (
        struct.pack("<HHi", 0x00B0, 11, 7)
        + struct.pack("<HHi", 0x00B0, 55, 3)
        + struct.pack("<HHi", 0x00B0, 19, 1)
        + struct.pack("<HHi", 0x00B1, 11, 123)
        + struct.pack("<HHq", 0x0ACB, 55, 123456789)
    )
    packets, rest = client.pdb.parse_stream(raw)
    assert rest == b""
    for pid, packet in packets:
        bot._dispatch(pid, packet)
    assert bot.status_params == {11: 7, 55: 3}


def test_connect_map_allocation_failure_clears_selection_and_levels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bot, wire = setup(monkeypatch, characters(row(202, "Selected", 7, 0, 8)), zone())
    monkeypatch.setattr(bot, "_login_server", lambda: ("127.0.0.1", 6121))
    origin = OSError("offline allocation failure")
    calls = 0

    def allocate(*_args: object, **_kwargs: object) -> Wire:
        nonlocal calls
        calls += 1
        if calls == 1:
            return wire
        assert bot.selected_character_snapshot == SelectedCharacterSnapshot(202, 0, 8, 4, 7, 1)
        assert bot.status_params == {}
        raise origin

    monkeypatch.setattr(client.socket, "create_connection", allocate)
    bot.status_params = {11: 99, 55: 99}
    with pytest.raises(OSError, match="offline") as caught:
        bot.connect()
    assert caught.value is origin
    assert bot.selected_character_snapshot is None
    assert bot.status_params == {}
    assert not bot._temporary_sockets
    assert bot.sock is None


def test_reconnect_discards_final_old_reader_state(monkeypatch: pytest.MonkeyPatch) -> None:
    bot = client.BotClient("offline", "not_a_credential", verbose=False)
    snapshot = SelectedCharacterSnapshot(202, 0, 8, 4, 7, 1)

    def old_close() -> None:
        assert bot.selected_character_snapshot is None
        bot.selected_character_snapshot = snapshot
        bot._dispatch(0x00B0, struct.pack("<HHi", 0x00B0, 55, 99))

    def login() -> tuple[str, int]:
        assert bot.selected_character_snapshot is None
        assert bot.status_params == {}
        return "127.0.0.1", 6121

    monkeypatch.setattr(bot, "close", old_close)
    monkeypatch.setattr(bot, "_login_server", login)
    monkeypatch.setattr(bot, "_char_server", lambda *_args: ("127.0.0.1", 5121))
    monkeypatch.setattr(bot, "_map_server", lambda *_args: None)
    assert bot.connect() is bot


@pytest.mark.parametrize("create", [False, True])
def test_empty_list_preserves_disabled_creation_semantics(
    monkeypatch: pytest.MonkeyPatch, create: bool
) -> None:
    bot, wire = setup(monkeypatch, characters(), zone())
    bot.create_flag = create
    expected = NotImplementedError if create else RuntimeError
    with pytest.raises(expected):
        bot._char_server("127.0.0.1", 6121)
    assert bot.selected_character_snapshot is None
    assert len(wire.sent) == 1
