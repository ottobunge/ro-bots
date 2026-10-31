"""The context-gate slice: state.shop_offer must surface a bound offer, and
the tick-path dialogue retry must hold while one is bound.

Leg 54 (b99e047f): the C6 BOUND tap fired (had_offer=True at the moved-on
invalidation) while state.shop_offer sampled null in 0/180 receipt samples -
so e593544d's blocked-stage close hold and 5c71a9e4's engage hold, both
gated on state.shop_offer, never fired, and the tick-path dialogue retry
(_retry_blocked_dialogue_on_tick, the twin of the c0f99258-held action-path
retry) re-began INSIDE the bound window (opened 69->72, stage 'opening').
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

from robots.app.playing_runtime import NPC_RETRY_CADENCE_S  # noqa: E402
from robots.domain.model import Goal  # noqa: E402
from tests.test_native_self_metadata_context import bind, proof_for  # noqa: E402
from tests.test_native_shop_selection import ready_shop  # noqa: E402


def _bound_offer_client(monkeypatch: pytest.MonkeyPatch):
    """The bind shape from tests/test_recovery_holds_bound_offer.py."""
    wire, client, receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    receive(struct.pack("<HHIIBH", 0xC6, 15, 73, 61, 4, 1201))
    bind(client, proof_for(wire))
    client._zeny_seed = 80
    state = client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None  # the offer is bound
    return client, state, receive


def test_bound_context_offer_surfaces_in_built_state(monkeypatch) -> None:
    """While the context offer is bound, EVERY build surfaces it in state."""
    client, state, _receive = _bound_offer_client(monkeypatch)
    assert state.shop_offer is not None
    again = client.build_native_state(Goal.GRIND)
    assert again.shop_offer is not None


def test_bound_offer_surfaces_through_the_blocked_resting_stage(monkeypatch) -> None:
    """Regression pin (probe-verified): the e2e-49 narrowed predicate keeps the
    bound offer alive - and surfaced - through the post-C6 resting stage
    (the dialogue clock expired, deny_origin 'timeout', stage 'blocked')."""
    client, _state, _receive = _bound_offer_client(monkeypatch)
    client._npc._expire(client._now() + 10.0)
    assert client._npc.failed
    assert client._npc.view.stage == "blocked"
    state = client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None
    assert state.shop_offer is not None


def test_bound_offer_surfaces_through_the_repeat_c4_remarker(monkeypatch) -> None:
    """Regression pin (probe-verified): the leg-46 law - the binding guard
    carries no raw-sequence term, so the dealer's repeat C4 dealtype marker
    re-bumping the dialogue cursor must not kill (or unsurface) the offer."""
    client, _state, receive = _bound_offer_client(monkeypatch)
    receive(struct.pack("<HI", 0xC4, 123))  # the repeat dealtype marker
    client.drain_native_events()
    state = client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None
    assert state.shop_offer is not None


def test_tick_path_dialogue_retry_holds_while_an_offer_is_bound(monkeypatch) -> None:
    """The tick-path twin of the action-path recovery hold (c0f99258).

    Leg 54: the tick retry began INSIDE the bound window (~+13s past the
    C5) - the fresh begin replaced the view, the shop context read a NEW
    exchange round (moved-on opened 69->72, stage 'opening') and the offer
    died before the decide-paced mint's first tick. While a bound offer
    exists, the tick retry must hold: the barrier owns the dispatch until
    the offer dies on its own terms.
    """
    client, _state, _receive = _bound_offer_client(monkeypatch)
    # the dialogue clock expires while the deal lives server-side (leg 54:
    # the C6 landed ~13s past the C5's dialogue deadline)
    client._npc._expire(client._now() + 10.0)
    assert client._npc.failed
    cursor_before = client._npc.cursor
    view_before = client._npc.view
    # the TICK path (kept alive by the keepalive pump) must hold like the
    # action path already does
    client._retry_blocked_dialogue_on_tick(client._now() + NPC_RETRY_CADENCE_S + 1.0)
    assert client._npc.cursor == cursor_before  # no re-begin fired
    assert client._npc.view is view_before
    # the next build must still see the bound deal (leg 54's kill: the
    # re-begin's fresh view read moved-on and the offer died unseen)
    state_after = client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is not None  # the offer SURVIVED
    assert state_after.shop_offer is not None  # and the state SURFACES it


def test_tick_path_dialogue_retry_still_rebegins_without_an_offer(monkeypatch) -> None:
    """The hold is narrow: with no bound offer the tick retry still fires."""
    wire, client, _receive, _sent, selection = ready_shop(monkeypatch)
    client.perform_native(selection)
    bind(client, proof_for(wire))
    client._zeny_seed = 80
    client.build_native_state(Goal.GRIND)
    assert client._shop_context.offer is None  # no C6: nothing bound
    client._npc._expire(client._now() + 10.0)
    assert client._npc.failed
    view_before = client._npc.view
    assert view_before is not None
    opened_before = view_before.opened_sequence
    client._retry_blocked_dialogue_on_tick(client._now() + NPC_RETRY_CADENCE_S + 1.0)
    view_after = client._npc.view
    assert view_after is not None
    assert view_after.opened_sequence > opened_before  # the re-begin fired
