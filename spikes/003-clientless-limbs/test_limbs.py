#!/usr/bin/env python3
"""Four-limb smoke harness for an explicitly supplied isolated disposable fixture.

No reusable login defaults. Supply a private manifest with exact identities.
All connection handshakes, limb polling, teardown cooldowns, and retry backoffs
share one absolute monotonic deadline (59 seconds by default, at most 60).
Party proof requires fresh post-reply current-party membership AND an exact
recipient accepted result. A stale roster alone is never acceptance evidence.

Usage: python3 test_limbs.py --fixture /private/operator-manifest.json
This command performs live game actions; offline regressions live in tests/.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import stat
import struct
import sys
import time
from collections.abc import Iterable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from client import BotClient, ACT_SIT, ACT_STAND  # noqa: E402


def validate_fixture(data):
    """Operator assertion of isolation; never discover or invent identities."""
    if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
        raise ValueError("unsupported fixture schema")
    if data.get("isolated_disposable") is not True:
        raise ValueError("explicit isolated_disposable opt-in required")
    try:
        if not ipaddress.ip_address(data["login_host"]).is_loopback:
            raise ValueError("loopback literal required")
    except (KeyError, ValueError) as exc:
        raise ValueError("loopback literal required") from exc
    if type(data.get("login_port")) is not int or not 1 <= data["login_port"] <= 65535:
        raise ValueError("explicit login_port required")
    accounts = data.get("accounts")
    if not isinstance(accounts, list) or len(accounts) != 2:
        raise ValueError("exactly two disposable fixture pairs required")
    for account in accounts:
        if not isinstance(account, dict):
            raise ValueError("fixture pair must be an object")
        for field in ("username", "password", "character"):
            value = account.get(field)
            if (
                not isinstance(value, str)
                or not value
                or "\x00" in value
                or len(value.encode()) > 23
            ):
                raise ValueError("invalid or missing fixture identity/credential field")
        if "pincode" in account:
            pin = account["pincode"]
            if type(pin) is not str or len(pin) != 4 or any(d not in "0123456789" for d in pin):
                message = "fixture pincode must be exactly four ASCII digits"
                raise ValueError(message)
        for field in ("account_id", "char_id"):
            if type(account.get(field)) is not int or not 0 < account[field] < 2**32:
                raise ValueError("explicit positive fixture IDs required")
    for field in ("username", "character", "account_id", "char_id"):
        if len({account[field] for account in accounts}) != 2:
            raise ValueError("fixture pairs must be distinct")
    return data


def load_fixture(path):
    """Read only a private, owned, regular manifest; refuse symlink traversal."""
    path = Path(path).absolute()
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("private manifest must not traverse symlinks")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd) as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError("manifest must be private and owned (chmod 600)")
        try:
            data = json.load(stream)
        except (ValueError, UnicodeError) as exc:
            raise ValueError("invalid private fixture manifest") from exc
    return validate_fixture(data)


class FixtureClient(BotClient):
    """Refuse server-advertised redirects outside the loopback fixture."""

    def _char_server(self, ip, port):
        if not ipaddress.ip_address(ip).is_loopback:
            raise ValueError("char-server redirect must be loopback")
        return super()._char_server(ip, port)

    def _map_server(self, ip, port):
        if not ipaddress.ip_address(ip).is_loopback:
            raise ValueError("map-server redirect must be loopback")
        return super()._map_server(ip, port)


class Budget:
    def __init__(self, seconds, *, clock=time.monotonic, sleep=time.sleep):
        if not 0 < seconds <= 60:
            raise ValueError("budget must be positive and at most 60 seconds")
        self.clock, self.sleep = clock, sleep
        self.deadline = clock() + seconds
        self.connect_not_before = clock()
        self.failed_connection = False
        self.unreleased_clients = []

    def remaining(self):
        remaining = self.deadline - self.clock()
        if remaining <= 0:
            raise TimeoutError("overall deadline exhausted")
        return remaining

    def pause(self, seconds):
        remaining = self.remaining()
        if seconds >= remaining:
            raise TimeoutError("insufficient overall budget for required delay")
        self.sleep(seconds)
        self.remaining()

    def wait(self, predicate, seconds):
        end = min(self.deadline, self.clock() + seconds)
        while self.clock() < end:
            self.remaining()
            value = predicate()
            if value:
                return value
            self.sleep(max(0, min(0.05, end - self.clock())))
        self.remaining()
        return None


def retry_delay(exc, budget):
    text = str(exc).lower()
    locked = (
        "already online" in text
        or "already logged" in text
        or any(token in text for token in ("result=8", "result=2"))
    )
    # Source: rathena/src/login/login.hpp AUTH_TIMEOUT=30000;
    # loginclif.cpp SC_NOTIFY_BAN results 2 and 8. Unknown handshake failures
    # are conservatively lock-capable; never retry them on the old 6s interval.
    delay = (
        30
        if (
            budget.failed_connection
            or locked
            or isinstance(exc, (ConnectionError, TimeoutError, RuntimeError))
        )
        else 6
    )
    budget.connect_not_before = max(budget.connect_not_before, budget.clock() + delay)
    budget.pause(delay)
    return "login-lock" if locked else "conservative-handshake" if delay == 30 else "limb"


fixture = None

results: list[tuple[str, bool, float, str]] = []


def health(clients):
    for client in clients:
        if client.rx_thread is None or not client.rx_thread.is_alive():
            raise RuntimeError("receive thread died")
        if getattr(client, "rx_error", None) or getattr(client, "dispatch_errors", []):
            raise RuntimeError("receive/dispatch errors invalidate evidence")


def run_limb(name, fn, budget, retries=1):
    clients = []
    start = budget.clock()
    detail = "FAIL not attempted"
    if budget.unreleased_clients:
        results.append((name, False, 0.0, "FAIL cleanup incomplete; further limbs prohibited"))
        return
    for attempt in range(retries + 1):
        clients.clear()
        budget.failed_connection = False

        exc = None
        try:
            budget.remaining()
            detail = fn(clients, budget)
            budget.remaining()
            health(clients)
        except Exception as error:
            exc = error
            if isinstance(error, (ConnectionError, TimeoutError, RuntimeError)):
                budget.connect_not_before = max(budget.connect_not_before, budget.clock() + 30)
            # Exceptions may include authentication material: classify, do not echo.
            detail = f"FAIL {type(error).__name__}"
            if any(
                token in str(error).lower() for token in ("result=8", "result=2", "already online")
            ):
                detail += " login-lock"
        finally:
            cleanup_failures = []
            for client in clients:
                try:
                    client.close()
                    if (
                        client.sock is not None
                        or client.rx_thread is not None
                        or getattr(client, "_temporary_sockets", [])
                    ):
                        raise RuntimeError("client resources remain after cleanup")
                except BaseException as cleanup_error:
                    cleanup_failures.append(type(cleanup_error).__name__)
                    budget.unreleased_clients.append(client)
            if clients:
                budget.connect_not_before = max(budget.connect_not_before, budget.clock() + 3)
        if cleanup_failures:
            detail = detail if not detail.startswith("OK") else "FAIL limb evidence invalidated"
            detail += "; cleanup failed: " + ",".join(cleanup_failures)
            break
        if detail.startswith("OK"):
            results.append((name, True, budget.clock() - start, detail))
            return
        if attempt < retries:
            try:
                retry_delay(exc or ValueError("limb failed"), budget)
            except TimeoutError:
                detail += "; retry skipped: required delay exceeds overall deadline"
                break
    results.append((name, False, budget.clock() - start, detail))


def connect_pair(clients, budget):
    if budget.unreleased_clients:
        raise RuntimeError("cleanup incomplete; connection prohibited")
    if fixture is None:
        raise ValueError("explicit fixture manifest required")
    validate_fixture(fixture)
    if budget.connect_not_before > budget.clock():
        budget.pause(budget.connect_not_before - budget.clock())
    for account in fixture["accounts"]:
        budget.remaining()
        client = FixtureClient(
            account["username"],
            account["password"],
            char_name=account["character"],
            login_ip=fixture["login_host"],
            login_port=fixture["login_port"],
            create_char=False,
            verbose=False,
            pincode=account.get("pincode"),
        )
        clients.append(client)
        # Contract with the independent client repair: absolute monotonic deadline.
        # Do not silently fall back to the unbounded legacy connect().
        try:
            client.connect(deadline=budget.deadline)
            budget.remaining()
            if (client.aid, client.gid) != (account["account_id"], account["char_id"]):
                raise ValueError("connected identity differs from exact fixture pair")
        except BaseException:
            budget.failed_connection = True
            budget.connect_not_before = max(budget.connect_not_before, budget.clock() + 30)
            raise
    budget.pause(1)
    return clients[0], clients[1]


def limb_chat(clients, budget):
    a, b = connect_pair(clients, budget)
    b.chat.clear()
    message = "limb-" + str(time.monotonic_ns())
    budget.remaining()
    a.say(message)
    got = budget.wait(
        lambda: next(
            ((gid, msg) for gid, msg in list(b.chat) if gid == a.aid and message in msg), None
        ),
        5,
    )
    return "OK fresh A chat relayed to B" if got else "FAIL no exact sender chat"


def movement_arrival_evidence(
    records: Iterable[tuple[float, int, bytes]], old: set[int], target: tuple[int, int]
) -> bool:
    """Fresh self 0x0087 snapshots both current and target coordinates at arrival.

    SELF has no actor ID: caller must use the exact mover's validated map stream.
    Entry identity excludes retained history, not arbitrary replay or reconnects.
    """
    for entry in records:
        if id(entry) in old:
            continue
        _ts, pid, raw = entry
        if pid != 0x0087:
            continue
        if len(raw) != 12 or struct.unpack_from("<H", raw)[0] != 0x0087:
            message = "malformed native self-walk acknowledgement"
            raise ValueError(message)
        data = raw[6:12]
        start = (data[0] << 2 | data[1] >> 6, (data[1] & 0x3F) << 4 | data[2] >> 4)
        end = ((data[2] & 0x0F) << 6 | data[3] >> 2, (data[3] & 0x03) << 8 | data[4])
        if start == end == target:
            return True
    return False


def limb_move(clients, budget):
    a, b = connect_pair(clients, budget)
    tx, ty = a.x, a.y + 1
    b.actors.clear()
    budget.remaining()
    a.move(tx, ty)
    seen = budget.wait(
        lambda: any(
            info.get("gid") == a.aid and (info.get("x"), info.get("y")) == (tx, ty)
            for info in list(b.actors.values())
        ),
        6,
    )
    if not seen:
        return "FAIL no A destination announcement"
    # Capture BEFORE send: a valid fast response can arrive before move returns.
    # The second same-target request makes native clif_walkok a current-position
    # snapshot once the retargeted walk reaches its zero-length path.
    old = {id(entry) for entry in list(a.raw_log)}
    budget.remaining()
    a.move(tx, ty)
    arrived = budget.wait(lambda: movement_arrival_evidence(list(a.raw_log), old, (tx, ty)), 6)
    return (
        "OK B saw exact A destination and fresh self acknowledgement proves arrival"
        if arrived
        else "FAIL no fresh self arrival acknowledgement"
    )


def limb_sit_stand(clients, budget):
    a, b = connect_pair(clients, budget)
    b.damage.clear()
    budget.remaining()
    a.sit()
    budget.pause(0.2)
    a.stand()

    def ordered():
        acts = [act for src, _tgt, _dmg, act in list(b.damage) if src == a.aid]
        return ACT_SIT in acts and ACT_STAND in acts[acts.index(ACT_SIT) + 1 :]

    return "OK B saw A sit then stand" if budget.wait(ordered, 5) else "FAIL no ordered sit/stand"


def wire_name(raw):
    return raw.split(b"\0", 1)[0].decode("utf-8", errors="strict")


def fresh_packets(client, old):
    return [entry for entry in list(client.raw_log) if id(entry) not in old]


def party_evidence(records, old, recipient, party_name):
    """Both fresh inviter result and current-party exact member are required."""
    accepted = member = False
    for entry in records:
        if id(entry) in old:
            continue
        _ts, pid, raw = entry
        if pid == 0x02C5 and len(raw) == 30:
            accepted |= (
                wire_name(raw[2:26]) == recipient["character"]
                and struct.unpack_from("<i", raw, 26)[0] == 2
            )
        if pid == 0x0AE4 and len(raw) == 89:
            member |= (
                struct.unpack_from("<II", raw, 2) == (recipient["account_id"], recipient["char_id"])
                and wire_name(raw[23:47]) == party_name
                and wire_name(raw[47:71]) == recipient["character"]
                and raw[22] == 0
            )
    return accepted and member


def limb_party(clients, budget):
    a, b = connect_pair(clients, budget)
    for client in (a, b):
        budget.remaining()
        client._send(struct.pack("<H", 0x0100))
    budget.pause(0.5)
    a.party_create_result = None
    a.party_members.clear()
    a.party_added.clear()
    party_name = "Spike" + str(time.monotonic_ns())[-16:]
    budget.remaining()
    a.party_create(party_name)
    if not budget.wait(lambda: a.party_create_result is not None, 8):
        return "FAIL no create ack"
    if a.party_create_result != 0:
        return "FAIL rejected create ack"
    if not budget.wait(lambda: bool(a.party_members), 8):
        return "FAIL no creation roster"
    # 0x02c6 carries PARTY NAME, not the inviter's character name (clif.cpp).
    old_invites = {id(entry) for entry in list(b.raw_log)}
    budget.remaining()
    a.party_invite(fixture["accounts"][1]["character"])

    def current_invitation():
        for _ts, pid, raw in fresh_packets(b, old_invites):
            if pid == 0x02C6 and len(raw) == 30 and wire_name(raw[6:30]) == party_name:
                party_id = struct.unpack_from("<I", raw, 2)[0]
                if party_id:
                    return party_id
        return None

    invitation = budget.wait(current_invitation, 8)
    if not invitation:
        return "FAIL no fresh current-party invitation on B"
    budget.remaining()
    b.party_reply(invitation, True)
    # Fail closed: only records arriving AFTER the reply returns are eligible.
    # A very fast valid response can be excluded here; false negatives are safer
    # than accepting a cached response. There is no wire invitation nonce.
    old_replies = {id(entry) for entry in list(a.raw_log)}
    observed = budget.wait(
        lambda: party_evidence(list(a.raw_log), old_replies, fixture["accounts"][1], party_name), 8
    )
    return (
        "OK fresh exact recipient accepted into current party"
        if observed
        else "FAIL no correlated post-reply acceptance"
    )


def main(argv=None):
    global fixture
    parser = argparse.ArgumentParser(description="Isolated disposable fixture smoke harness")
    parser.add_argument(
        "--fixture", type=Path, required=True, help="private operator-supplied manifest"
    )
    parser.add_argument("--budget", type=float, default=59, help="overall seconds, maximum 60")
    args = parser.parse_args(argv)
    try:
        fixture = load_fixture(args.fixture)
        budget = Budget(args.budget)
    except OSError, ValueError:
        print("FAILED: invalid private fixture configuration/budget (no connection attempted)")
        return 1
    results.clear()
    start = budget.clock()
    for name, fn in (
        ("chat", limb_chat),
        ("movement", limb_move),
        ("sit-stand", limb_sit_stand),
        ("party", limb_party),
    ):
        run_limb(name, fn, budget)
    total = budget.clock() - start
    for name, ok, elapsed, detail in results:
        print(f"{name}: {'PASS' if ok else 'FAIL'} ({elapsed:.2f}s) {detail}")
    ok = len(results) == 4 and all(result[1] for result in results) and total < args.budget
    print(
        f"VERDICT: {'SMOKE PASS' if ok else 'FAILED'} ({total:.2f}s; not general adapter validation)"
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
