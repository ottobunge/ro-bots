"""A bound offer survives the dialogue recovery's re-begin.

Leg 50 (the buy proof): the C6 BOUND survived the leg-49 clock killer
(bf93474a worked at its own layer), but the offer then died to
`bound-deal-lost moved-on=True` — the dialogue recovery's OWN re-begin fired
inside the bound window (the retry budget re-arms the dialogue, the fresh
begin replaces the view, and the shop context reads a NEW exchange round).
The deal is alive server-side even though the dialogue clock expired: while a
bound offer exists, the recovery must hold (the barrier stays, no re-begin)
until the offer dies on its own terms (the exchange gone / identity loss /
new round from a real click / the 300s TTL).
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
for candidate in (str(REPO / "src"), str(REPO), str(REPO / "tests")):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import pytest  # noqa: E402

from robots.domain.model import Goal  # noqa: E402
from tests.test_native_self_metadata_context import bind, proof_for  # noqa: E402
from tests.test_native_shop_selection import ready_shop  # noqa: E402


def _bound_offer_client(monkeypatch: pytest.MonkeyPatch):
    wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    receive(struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201))
    bind(client, proof_for(wire))
    client._zeny_seed = 80
    client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None  # the offer is bound
    return client


def test_recovery_rebegin_holds_while_an_offer_is_bound(monkeypatch) -> None:
    client = _bound_offer_client(monkeypatch)
    # the dialogue clock expires while the deal lives server-side
    client._npc._expire(client._now() + 10.0)
    assert client._npc.failed
    cursor_before = client._npc.cursor
    view_before = client._npc.view
    # the recovery must NOT re-begin: the re-begin replaces the view and the
    # shop context reads a NEW exchange round (leg 50: bound-deal-lost)
    assert client._retry_blocked_dialogue() is True  # the barrier owns it
    assert client._shop_context.offer is not None  # the offer SURVIVED
    assert client._npc.cursor == cursor_before  # no re-begin fired
    assert client._npc.view is view_before
