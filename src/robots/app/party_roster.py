"""The received party roster: candidate resolution for invites.

The live client's ``party_members`` is a LIST of ``{name, aid}`` dicts; the
legacy simulation fake is a ``name -> aid`` dict. Both invite limbs (guild
CZ_REQ_JOIN_GUILD 0x0168 = target_AID, and party) resolve the candidate
through here and fail closed on an unknown name — leg 33 crashed ten times
on ``.get()`` called against the list.
"""

from __future__ import annotations

from typing import Any


def guild_candidate_aid(members: Any, player: str) -> int:
    """The candidate's account id, or 0 when the roster does not name them."""
    if isinstance(members, dict):
        return int(members.get(player, 0))
    for member in members or ():
        if isinstance(member, dict) and member.get("name") == player:
            return int(member.get("aid", 0))
    return 0
