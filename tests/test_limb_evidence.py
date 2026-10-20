"""Deterministic offline regressions; never open a game or SQL connection."""

import importlib.util
import json
import struct
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any, Protocol, TypedDict

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPIKE = ROOT / "spikes" / "003-clientless-limbs"
sys.path.insert(0, str(SPIKE))
spec = importlib.util.spec_from_file_location("limb_harness", SPIKE / "test_limbs.py")
assert spec is not None
assert spec.loader is not None
limbs = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = limbs
spec.loader.exec_module(limbs)


class BudgetLike(Protocol):
    def wait(self, predicate: Callable[[], object], seconds: float) -> object: ...


class PartyState(TypedDict, total=False):
    name: str
    replied: bool
    sent: bool


def fixture_document() -> dict[str, Any]:
    # Explicit synthetic offline data; not a reusable server credential.
    return {
        "schema": 1,
        "isolated_disposable": True,
        "login_host": "127.0.0.1",
        "login_port": 6900,
        "accounts": [
            {
                "username": "offline-a",
                "password": "test-only-a",
                "account_id": 11,
                "character": "OfflineA",
                "char_id": 21,
            },
            {
                "username": "offline-b",
                "password": "test-only-b",
                "account_id": 12,
                "character": "OfflineB",
                "char_id": 22,
            },
        ],
    }


def test_fixture_requires_private_explicit_isolated_manifest(tmp_path):
    path = tmp_path / "fixture.json"
    path.write_text(json.dumps(fixture_document()))
    path.chmod(0o600)
    assert limbs.load_fixture(path)["accounts"][0]["char_id"] == 21
    path.chmod(0o644)
    with pytest.raises(ValueError, match="private"):
        limbs.load_fixture(path)
    path.chmod(0o600)
    for key, value in [("isolated_disposable", False), ("login_host", "203.0.113.1")]:
        data = fixture_document()
        data[key] = value
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError, match=r"isolated_disposable|loopback"):
            limbs.load_fixture(path)
    data = fixture_document()
    del data["accounts"][0]["password"]
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="identity/credential"):
        limbs.load_fixture(path)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_deadline_exhaustion_stops_waits_and_retries():
    clock = Clock()
    budget = limbs.Budget(2, clock=clock.monotonic, sleep=clock.sleep)
    with pytest.raises(TimeoutError):
        budget.wait(lambda: False, 8)
    assert clock.now == 102
    with pytest.raises(TimeoutError):
        budget.pause(1)
    assert clock.now == 102


def test_lock_retry_waits_thirty_seconds_or_aborts():
    clock = Clock()
    budget = limbs.Budget(60, clock=clock.monotonic, sleep=clock.sleep)
    limbs.retry_delay(RuntimeError("banned, result=8"), budget)
    assert clock.sleeps == [30]
    short = limbs.Budget(20, clock=clock.monotonic, sleep=clock.sleep)
    with pytest.raises(TimeoutError):
        limbs.retry_delay(RuntimeError("auth refused, result=2"), short)
    assert clock.sleeps == [30]


def test_connect_pair_propagates_same_deadline_and_exact_ids(monkeypatch):
    clock = Clock()
    budget = limbs.Budget(10, clock=clock.monotonic, sleep=clock.sleep)
    seen: list[float] = []

    class Client:
        def __init__(self, username: str, password: str, **kwargs: object) -> None:
            self.aid = 11 if username == "offline-a" else 12
            self.gid = 21 if username == "offline-a" else 22

        def connect(self, *, deadline: float) -> None:
            seen.append(deadline)

    monkeypatch.setattr(limbs, "FixtureClient", Client)
    monkeypatch.setattr(limbs, "fixture", fixture_document())
    clients: list[Client] = []
    limbs.connect_pair(clients, budget)
    assert seen == [110, 110]
    fixture = fixture_document()
    fixture["accounts"][0]["char_id"] = 99
    monkeypatch.setattr(limbs, "fixture", fixture)
    with pytest.raises(ValueError, match="identity"):
        limbs.connect_pair([], budget)


def result_packet(name: str) -> bytes:
    return struct.pack("<H", 0x02C5) + name.encode().ljust(24, b"\0") + struct.pack("<i", 2)


def member_packet(
    name: str = "OfflineB", aid: int = 12, gid: int = 22, party: str = "unique"
) -> bytes:
    raw = bytearray(89)
    struct.pack_into("<HII", raw, 0, 0x0AE4, aid, gid)
    raw[23:47] = party.encode().ljust(24, b"\0")
    raw[47:71] = name.encode().ljust(24, b"\0")
    return bytes(raw)


def test_acceptance_requires_fresh_exact_recipient_and_current_party():
    account = fixture_document()["accounts"][1]
    old = (1, 0x02C5, result_packet("OfflineB"))
    member = (2, 0x0AE4, member_packet())
    good = (3, 0x02C5, result_packet("OfflineB"))
    assert not limbs.party_evidence([old, member], {id(old)}, account, "unique")
    assert not limbs.party_evidence(
        [(3, 0x02C5, result_packet("SomeoneElse")), member], set(), account, "unique"
    )
    assert not limbs.party_evidence(
        [good, (2, 0x0AE4, member_packet(aid=99))], set(), account, "unique"
    )
    assert not limbs.party_evidence(
        [good, (2, 0x0AE4, member_packet(party="old"))], set(), account, "unique"
    )
    assert limbs.party_evidence([good, member], set(), account, "unique")


def test_stale_two_member_roster_is_not_acceptance(monkeypatch):
    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)
    a = SimpleNamespace(party_create_result=None, party_members=[], party_added=[], raw_log=[])
    b = SimpleNamespace(
        party_members=[{"name": "OfflineA"}, {"name": "OfflineB"}],
        raw_log=[(1, 0x02C5, result_packet("OfflineB"))],
    )
    a._send = b._send = lambda _: None

    def create(name: str) -> None:
        a.party_create_result = 0
        a.party_members = [{"name": "OfflineA"}]

    a.party_create = create
    a.party_invite = lambda _: None
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (a, b))
    monkeypatch.setattr(limbs, "fixture", fixture_document())
    assert limbs.limb_party([], budget).startswith("FAIL")


def seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "seed_fixture", SPIKE / "scripts" / "seed_fixture.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def seed_snapshot() -> dict[str, Any]:
    return {
        "engines": {"login": "InnoDB", "char": "InnoDB", "skill": "InnoDB"},
        "login": [
            {"account_id": 11, "userid": "offline-a"},
            {"account_id": 12, "userid": "offline-b"},
        ],
        "char": [
            {"char_id": 21, "account_id": 11, "name": "OfflineA", "online": 0},
            {"char_id": 22, "account_id": 12, "name": "OfflineB", "online": 0},
        ],
    }


def test_seed_offline_validation_rejects_ownership_online_and_nontransactional():
    seed = seed_module()
    seed.validate_snapshot(fixture_document(), seed_snapshot())
    for field, value in [("account_id", 99), ("online", 1), ("name", "offlineb")]:
        snapshot = seed_snapshot()
        snapshot["char"][1][field] = value
        with pytest.raises(ValueError, match=r"ownership|offline"):
            seed.validate_snapshot(fixture_document(), snapshot)
    snapshot = seed_snapshot()
    snapshot["engines"]["char"] = "MyISAM"
    with pytest.raises(ValueError, match="InnoDB"):
        seed.validate_snapshot(fixture_document(), snapshot)


def test_seed_render_has_no_passwords_and_guard_precedes_fixture_writes():
    seed = seed_module()
    script = seed.render_seed(fixture_document(), servers_stopped=True)
    assert "test-only" not in script
    assert "FOR UPDATE" in script
    assert script.index("fixture ownership/offline mismatch") < script.index("UPDATE `char`")
    assert script.index("ROLLBACK") < script.index("UPDATE `char`")
    with pytest.raises(ValueError, match="stopped"):
        seed.render_seed(fixture_document(), servers_stopped=False)


def test_lock_delay_cannot_be_bypassed_by_next_limb(monkeypatch):
    clock = Clock()
    budget = limbs.Budget(20, clock=clock.monotonic, sleep=clock.sleep)
    with pytest.raises(TimeoutError):
        limbs.retry_delay(RuntimeError("banned, result=8"), budget)
    seen: list[int] = []
    monkeypatch.setattr(limbs, "FixtureClient", lambda *_args, **_kwargs: seen.append(1))
    monkeypatch.setattr(limbs, "fixture", fixture_document())
    with pytest.raises(TimeoutError):
        limbs.connect_pair([], budget)
    assert not seen


def test_live_thread_with_recorded_receive_error_cannot_pass():
    client = SimpleNamespace(
        rx_thread=SimpleNamespace(is_alive=lambda: True),
        rx_error=ValueError("framing"),
        dispatch_errors=[],
    )
    with pytest.raises(RuntimeError):
        limbs.health([client])


def test_run_limb_overall_exhaustion_does_not_start_second_attempt():
    clock = Clock()
    budget = limbs.Budget(2, clock=clock.monotonic, sleep=clock.sleep)
    calls: list[int] = []

    def failure(clients: list[object], deadline: BudgetLike) -> None:
        calls.append(1)
        deadline.wait(lambda: False, 8)

    limbs.results.clear()
    limbs.run_limb("offline", failure, budget)
    assert calls == [1]
    assert limbs.results[0][1] is False
    assert clock.now == 102


def test_server_redirects_cannot_escape_loopback():
    client = limbs.FixtureClient("offline", "offline-only", char_name="Offline")
    with pytest.raises(ValueError, match="loopback"):
        client._char_server("203.0.113.2", 6121)
    with pytest.raises(ValueError, match="loopback"):
        client._map_server("203.0.113.2", 5121)


@pytest.mark.parametrize("case", ["stale-result", "wrong-recipient", "wrong-invitation", "success"])
def test_party_whole_flow_requires_post_reply_correlated_evidence(monkeypatch, case):
    clock = Clock()
    a = SimpleNamespace(party_create_result=None, party_members=[], party_added=[], raw_log=[])
    b = SimpleNamespace(raw_log=[], party_members=[{"name": "OfflineA"}, {"name": "OfflineB"}])
    a._send = b._send = lambda _: None
    current: PartyState = {}

    def create(name: str) -> None:
        current["name"] = name
        a.party_create_result = 0
        a.party_members = [{"name": "OfflineA"}]

    def invite(recipient: str) -> None:
        name = "stale-party" if case == "wrong-invitation" else current["name"]
        b.raw_log.append(
            (1, 0x02C6, struct.pack("<HI", 0x02C6, 77) + name.encode().ljust(24, b"\0"))
        )

    def reply(pid: int, accept: bool) -> None:
        assert (pid, accept) == (77, True)
        current["replied"] = True
        if case == "stale-result":
            a.raw_log.append((2, 0x02C5, result_packet("OfflineB")))

    def sleep(seconds: float) -> None:
        clock.sleep(seconds)
        if current.get("replied") and not current.get("sent"):
            current["sent"] = True
            a.raw_log.append((3, 0x0AE4, member_packet(party=current["name"])))
            if case != "stale-result":
                nick = "Other" if case == "wrong-recipient" else "OfflineB"
                a.raw_log.append((3, 0x02C5, result_packet(nick)))

    a.party_create, a.party_invite, b.party_reply = create, invite, reply
    monkeypatch.setattr(limbs, "connect_pair", lambda *_: (a, b))
    monkeypatch.setattr(limbs, "fixture", fixture_document())
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=sleep)
    result = limbs.limb_party([], budget)
    assert result.startswith("OK") == (case == "success")


def test_final_failed_handshake_preserves_lock_for_following_limb():
    clock = Clock()
    budget = limbs.Budget(59, clock=clock.monotonic, sleep=clock.sleep)

    def locked(_clients: list[object], _budget: BudgetLike) -> None:
        msg = "banned, result=8"
        raise RuntimeError(msg)

    limbs.run_limb("locked", locked, budget, retries=0)
    assert budget.connect_not_before >= 130


@pytest.mark.parametrize("value", [float("nan"), float("inf"), 0, -1, 61])
def test_invalid_overall_budget_is_rejected(value):
    with pytest.raises(ValueError, match="budget"):
        limbs.Budget(value)


def test_malformed_fixture_pair_fails_closed():
    data = fixture_document()
    data["accounts"][0] = "not-an-account-object"
    with pytest.raises(ValueError, match="pair must be an object"):
        limbs.validate_fixture(data)


def test_main_requires_manifest_without_instantiating_client(monkeypatch):
    monkeypatch.setattr(
        limbs, "FixtureClient", lambda *_args, **_kwargs: pytest.fail("network forbidden")
    )
    with pytest.raises(SystemExit) as exc:
        limbs.main([])
    assert exc.value.code == 2
