"""Shared fixtures: a deterministic BotState factory and test doubles."""

import pytest

from robots.domain.model import ActorRef, BotState, ChatLine, Goal, PartyInvite


def make_state(**overrides: object) -> BotState:
    """A level-42 swordsman grinding Prontera South defaults, overridable."""
    base: dict[str, object] = {
        "name": "SpikeBot01",
        "job": "Swordsman",
        "base_level": 42,
        "hp": 800,
        "max_hp": 1000,
        "sp": 60,
        "max_sp": 80,
        "map_name": "prt_fild08",
        "x": 120,
        "y": 74,
        "goal": Goal.GRIND,
        "in_party": False,
        "nearby": (
            ActorRef(id=10001, name="Poring", kind="monster", distance=3.0),
            ActorRef(id=10002, name="Condor", kind="monster", distance=7.5),
        ),
        "inventory": {"Jellopy": 23, "Red Potion": 5},
        "pending_invites": (),
        "recent_chat": (),
    }
    base.update(overrides)
    return BotState(**base)  # type: ignore[arg-type]


@pytest.fixture
def state() -> BotState:
    return make_state()


@pytest.fixture
def town_state() -> BotState:
    return make_state(
        map_name="prontera",
        goal=Goal.IDLE_TOWN,
        nearby=(ActorRef(id=20001, name="Trader", kind="player", distance=4.0),),
        recent_chat=(ChatLine(channel="public", sender="Trader", text="hi bot", at=1.0),),
    )


@pytest.fixture
def invited_state() -> BotState:
    return make_state(
        pending_invites=(PartyInvite(from_name="PartyLeader", at=2.0),),
    )
