"""Second bounded protocol repair cycle: offline, compiler-backed regressions."""

import ast
import hashlib
import importlib.util
import os
import re
import secrets
import shlex
import struct
import subprocess
import sys
from collections import deque
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes/003-clientless-limbs"
sys.path.insert(0, str(SPIKE))


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_obsolete_probe_has_no_literal_credentials_or_import_connections(monkeypatch):

    calls = []
    monkeypatch.setattr(client.BotClient, "connect", lambda *_a, **_k: calls.append(1))
    path = SPIKE / "scripts/probe_map.py"
    tree = ast.parse(path.read_text())
    literal_clients = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "BotClient"
        and any(isinstance(arg, ast.Constant) for arg in node.args[:2])
    ]
    has_literal_credentials = bool(literal_clients)
    assert not has_literal_credentials, "obsolete probe contains literal credential constructions"
    module = load_module("retired_probe", path)
    assert calls == []
    assert module.main([]) != 0
    assert calls == []


def test_obsolete_generator_is_fail_closed_without_eval_or_legacy_routes():
    path = SPIKE / "scripts/gen_packetdb.py"
    tree = ast.parse(path.read_text())
    executable = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id in {"eval", "exec"}
    ]
    assert not executable, "alternate generator executes source text"
    module = load_module("retired_generator", path)
    assert not hasattr(module, "eval_cond")
    assert not hasattr(module, "derive")
    assert module.main([]) != 0


client = load_module("rereview_client", SPIKE / "client.py")


@pytest.fixture
def limbs():
    return load_module("rereview_limbs", SPIKE / "test_limbs.py")


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


@pytest.mark.parametrize("wire_id", [11, 21])
def test_movement_accepts_only_account_wire_actor(limbs, monkeypatch, wire_id):

    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)
    b = SimpleNamespace(actors={})
    a = SimpleNamespace(aid=11, gid=21, x=165, y=145, raw_log=[])
    sends = []

    def move(x, y):
        sends.append((x, y))
        b.actors[wire_id] = {"gid": wire_id, "char_id": 21, "x": x, "y": y}
        if len(sends) == 2:
            # Fresh native SELF acknowledgement: both current and target cells.
            packed = (x << 30) | (y << 20) | (x << 10) | y
            raw = struct.pack("<HI", 0x0087, 123) + packed.to_bytes(5, "big") + b"\x88"
            a.raw_log.append((clock.now, 0x0087, raw))

    a.move = move
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (a, b))
    assert limbs.limb_move([], budget).startswith("OK") == (wire_id == a.aid)
    assert len(sends) == (2 if wire_id == a.aid else 1)


def fixture_document() -> dict[str, Any]:

    return {
        "schema": 1,
        "isolated_disposable": True,
        "login_host": "127.0.0.1",
        "login_port": 6900,
        "accounts": [
            {
                "username": f"offline-{i}",
                "password": secrets.token_hex(8),
                "character": f"Offline{i}",
                "account_id": 10 + i,
                "char_id": 20 + i,
            }
            for i in (1, 2)
        ],
    }


@pytest.mark.parametrize("error_type", [OSError, ValueError, ConnectionError, RuntimeError])
@pytest.mark.parametrize("stage", ["char", "map"])
@pytest.mark.parametrize("retries", [0, 1])
def test_every_failed_attempt_preserves_lock_across_limbs(
    limbs, monkeypatch, error_type, stage, retries
):
    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)
    seen = []
    monkeypatch.setattr(limbs.time, "monotonic", clock.monotonic)
    monkeypatch.setattr(limbs, "fixture", fixture_document())

    def login(bot):
        bot.aid, bot.gid = 11, 21
        seen.append(clock.now)
        return "127.0.0.1", 1

    def fail(*_args):
        raise error_type()

    monkeypatch.setattr(limbs.FixtureClient, "_login_server", login)
    monkeypatch.setattr(
        limbs.FixtureClient,
        "_char_server",
        fail if stage == "char" else lambda *_: ("127.0.0.1", 1),
    )
    monkeypatch.setattr(limbs.FixtureClient, "_map_server", fail)
    limbs.run_limb("first", limbs.connect_pair, budget, retries=retries)
    assert seen == ([100.0] if retries == 0 else [100.0, 130.0])
    assert budget.connect_not_before >= seen[-1] + 30
    limbs.run_limb("next", limbs.connect_pair, budget, retries=0)
    assert seen == [100.0, 130.0]
    assert all(not result[1] for result in limbs.results)


@pytest.mark.parametrize("success", [False, True])
@pytest.mark.parametrize("stuck", [False, True])
def test_cleanup_attempts_all_clients_blocks_retry_and_following_limb(limbs, success, stuck):

    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)
    closed, attempts = [], []
    clients = []
    secret = "sentinel-not-for-output"
    for index in range(2):
        participant = SimpleNamespace(
            sock=object(),
            rx_thread=SimpleNamespace(is_alive=lambda: True),
            rx_error=None,
            dispatch_errors=[],
        )

        def close(p=participant, i=index):
            closed.append(i)
            if i == 0:
                if not stuck:
                    raise RuntimeError(secret)
            else:
                p.sock = p.rx_thread = None

        participant.close = close
        clients.append(participant)

    def limb(participants, _budget):
        attempts.append(1)
        participants.extend(clients)
        if not success:
            raise ValueError(secret)
        return "OK fake limb evidence"

    limbs.run_limb("first", limb, budget)
    assert closed == [0, 1]
    assert len(attempts) == 1
    assert not limbs.results[-1][1]
    assert "cleanup" in limbs.results[-1][3]
    assert secret not in limbs.results[-1][3]
    if not success:
        assert "ValueError" in limbs.results[-1][3]
    assert budget.unreleased_clients[0] is clients[0]
    limbs.run_limb("next", limb, budget)
    assert len(attempts) == 1
    assert not limbs.results[-1][1]


def test_connect_preserves_origin_when_cleanup_also_fails(monkeypatch):

    bot = client.BotClient("offline", secrets.token_hex(8), verbose=False)
    origin = ValueError("sentinel-origin-secret")
    cleanup = RuntimeError("sentinel-cleanup-secret")
    calls = []

    def close():
        calls.append(1)
        if len(calls) > 1:
            raise cleanup

    def login():
        raise origin

    monkeypatch.setattr(bot, "close", close)
    monkeypatch.setattr(bot, "_login_server", login)
    with pytest.raises(ValueError, match="sentinel-origin") as caught:
        bot.connect()
    assert caught.value is origin
    assert bot.cleanup_errors == [cleanup]
    assert all("sentinel" not in note for note in origin.__notes__)


@pytest.fixture(scope="session")
def native_layout(tmp_path_factory):

    native = ROOT / "rathena"
    authority = {
        "rathena/config.log": "6bb759d7b65d463ecd38ca81f484659ec2dc6e7885b017a964b9c611114e9d78",
        "rathena/src/common/packets.hpp": (
            "c92279bf163e9546b649397638c19e57c3eb515b49e841c13f88a5fb97bba693"
        ),
        "rathena/src/map/packets_struct.hpp": (
            "5ab5ef13d2a1cdc60d84dcaf2e3be0b6e316b9630e61c3ac7ba0f930d4d31287"
        ),
    }
    for relative in (
        "rathena/config.log",
        "rathena/src/common/packets.hpp",
        "rathena/src/map/packets_struct.hpp",
    ):
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        assert actual == authority[relative]
    config = (native / "config.log").read_text()
    match = re.search(r"^CPPFLAGS='([^']*)'", config, re.M)
    assert match is not None
    flags = [flag for flag in shlex.split(match[1]) if flag.startswith("-D")]
    assert "-DPACKETVER=20180704" in flags
    assert "-DPRERE" in flags
    header = (native / "src/map/packets_struct.hpp").read_text()
    declarations = []
    for name in ("packet_unit_walking", "packet_spawn_unit", "packet_idle_unit"):
        excerpt = re.search(
            rf"struct {name}\s*\{{.*?\}} __attribute__\(\(packed\)\);", header, re.S
        )
        assert excerpt is not None
        declarations.append(excerpt[0])
    source = "#include <common/packets.hpp>\n#include <cstdio>\n#include <cstddef>\n"
    source += "\n".join(declarations)
    source += r"""
static_assert(PACKETVER_MAIN_NUM == 20180704);
#ifdef PACKETVER_RE
#error not MAIN
#endif
int main() {
    std::printf("%zu %zu %zu %zu %zu %zu %zu %zu %zu %zu %zu %zu",
        sizeof(CHARACTER_INFO), offsetof(CHARACTER_INFO, name),
        offsetof(CHARACTER_INFO, CharNum), sizeof(packet_unit_walking),
        offsetof(packet_unit_walking, AID), offsetof(packet_unit_walking, GID),
        offsetof(packet_unit_walking, MoveData), offsetof(packet_unit_walking, name),
        sizeof(packet_spawn_unit), offsetof(packet_spawn_unit, name),
        sizeof(packet_idle_unit), offsetof(packet_idle_unit, name));
}
"""
    exe = tmp_path_factory.mktemp("native-layout") / "oracle"
    subprocess.run(
        [
            "g++",
            "-x",
            "c++",
            "-std=c++17",
            *flags,
            "-I" + str(native / "src"),
            "-I" + str(native / "3rdparty/libconfig"),
            "-o",
            str(exe),
            "-",
        ],
        input=source,
        text=True,
        capture_output=True,
        check=True,
        timeout=30,
    )
    output = subprocess.run(
        [str(exe)], text=True, capture_output=True, check=True, timeout=5
    ).stdout
    values = list(map(int, output.split()))
    assert values == [155, 88, 118, 110, 5, 9, 63, 86, 103, 79, 104, 80]
    return values


class FakeSocket:
    def __init__(self, chunks: list[bytes]) -> None:

        self.chunks = deque(chunks)
        self.sent: list[bytes] = []
        self.closed = False

    def settimeout(self, value):
        pass

    def recv(self, count):
        assert self.chunks, "unexpected receive"
        chunk = self.chunks.popleft()
        if len(chunk) > count:
            self.chunks.appendleft(chunk[count:])
        return chunk[:count]

    def sendall(self, raw):
        self.sent.append(raw)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.closed = True


@pytest.mark.parametrize("slots", [(5,), (2, 7)])
def test_character_selection_uses_native_sparse_wire_slot(native_layout, monkeypatch, slots):

    size, name_offset, slot_offset = native_layout[:3]
    bot = client.BotClient("offline", secrets.token_hex(8), char_name="Selected", verbose=False)
    bot.aid = 11
    raw = bytearray(27 + size * len(slots))
    struct.pack_into("<HH", raw, 0, 0x006B, len(raw))
    for index, slot in enumerate(slots):
        offset = 27 + index * size
        struct.pack_into("<I", raw, offset, 21 + index)
        name = b"Selected" if index == len(slots) - 1 else b"Other"
        raw[offset + name_offset : offset + name_offset + 24] = name.ljust(24, b"\0")
        raw[offset + slot_offset] = slot
    zone = bytearray(28)
    struct.pack_into("<HI", zone, 0, 0x0071, 21 + len(slots) - 1)
    zone[22:26] = bytes([127, 0, 0, 1])
    struct.pack_into("<H", zone, 26, 5121)
    pin_status = struct.pack("<HIIH", 0x08B9, 123, 11, 0)
    sock = FakeSocket([struct.pack("<I", 11) + bytes(raw) + pin_status + bytes(zone)])
    monkeypatch.setattr(client.socket, "create_connection", lambda *_a, **_k: sock)
    assert bot._char_server("127.0.0.1", 1) == ("127.0.0.1", 5121)
    assert sock.sent[-1] == struct.pack("<HB", 0x0066, slots[-1])
    assert bot.gid == 21 + len(slots) - 1
    assert sock.closed


def test_walking_name_matches_pinned_unaltered_native_struct(native_layout):

    size, aid, gid, move, name = native_layout[3:8]
    raw = bytearray(size)
    struct.pack_into("<HH", raw, 0, 0x09FD, size)
    struct.pack_into("<I", raw, aid, 11)
    struct.pack_into("<I", raw, gid, 21)
    raw[name : name + 24] = b"OfflineA".ljust(24, b"\0")
    parsed = client.BotClient._parse_actor_entry(0x09FD, bytes(raw))
    assert parsed["name"] == "OfflineA"
    assert (parsed["gid"], parsed["char_id"]) == (11, 21)
    assert move == 63


def test_actor_size_metadata_matches_native_compiler(native_layout):
    assert {
        0x09FD: native_layout[3],
        0x09FE: native_layout[8],
        0x09FF: native_layout[10],
    } == client.pdb.ACTOR_ENTRY_LEN


def test_fifo_manifest_is_nonblocking_and_rejected(limbs, monkeypatch, tmp_path):

    path = tmp_path / "fixture-fifo"
    os.mkfifo(path, 0o600)
    real_open = limbs.os.open

    def checked_open(filename, flags):
        assert flags & os.O_NONBLOCK, "FIFO open would block before regular-file check"
        return real_open(filename, flags)

    monkeypatch.setattr(limbs.os, "open", checked_open)
    with pytest.raises(ValueError, match="private"):
        limbs.load_fixture(path)


def test_failed_socket_release_is_retained_and_blocks_connect(monkeypatch):

    bot = client.BotClient("offline", secrets.token_hex(8), verbose=False)

    class CannotClose:
        def shutdown(self, how):
            pass

        def close(self):
            raise OSError()

    sock = CannotClose()
    bot.sock = sock
    with pytest.raises(RuntimeError, match="socket"):
        bot.close()
    assert bot.sock is sock
    monkeypatch.setattr(bot, "_login_server", lambda: pytest.fail("unsafe socket reuse"))
    with pytest.raises(RuntimeError, match="socket"):
        bot.connect()
    assert bot.sock is sock
