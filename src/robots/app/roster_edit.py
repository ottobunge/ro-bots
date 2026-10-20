"""Free edits on an immutable SocietyRoster (ADR-008 write path).

The roster is a plain object (not frozen), but its members are frozen
dataclasses, so edits produce *new* persona/group objects instead of
mutating: :func:`with_persona_edited` swaps one persona,
:func:`with_group_schedule` replaces one group's schedule. WorldState keeps
these as module functions so the roster type itself stays free of
dashboard concerns.
"""

from dataclasses import replace

from robots.society.models import Schedule
from robots.society.society import SocietyRoster


def with_persona_edited(roster: SocietyRoster, persona_id: str, **fields: object) -> SocietyRoster:
    """Return a new roster with ``persona_id``'s fields replaced (frozen swap)."""
    if persona_id not in roster.personas:
        raise KeyError(persona_id)
    persona = replace(roster.personas[persona_id], **fields)  # type: ignore[arg-type]
    personas = {**roster.personas, persona_id: persona}
    return SocietyRoster(roster.groups, personas, roster.graph, roster.reputation)


def with_group_schedule(
    roster: SocietyRoster, persona_id: str, schedule: Schedule
) -> SocietyRoster:
    """Return a new roster with the persona's group schedule replaced."""
    group = next((g for g in roster.groups if persona_id in g.member_ids), None)
    if group is None:
        raise KeyError(persona_id)
    new_group = replace(group, schedule=schedule)
    groups = [new_group if g is group else g for g in roster.groups]
    return SocietyRoster(groups, roster.personas, roster.graph, roster.reputation)
