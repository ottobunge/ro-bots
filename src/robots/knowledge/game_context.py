"""Bounded game-knowledge lines for the decide context (criteria 4 and 10).

Composes, for one tick's ``BotState``:

- a self combat line from the received stats (the six basic stats arrive on
  0x00BD; the calculators project atk/matk/hit/flee/def2/mdef2),
- up to three item projection lines for the numeric inventory ids
  (``"Chrysalis: sellable 4z; equip: no bonus (misc-class)"``) so CLEF can
  weigh equip vs sell vs store, and
- the target-monster line plus a map line from the corpora (criterion 10).

Absent corpora degrade to zero lines; every line is length-bounded and the
whole bundle is capped at ``MAX_DECIDE_LINES`` so the decide payload budget
holds. When the tick's free text (explicit topics such as objective/want
wording, recent chat, NPC pages) names a corpus item or mob — e.g. the
Emperium for a guild objective — a few ``queries.mention_lines`` ride along
inside the same cap.
"""

from collections.abc import Sequence

from robots.domain.model import BotState
from robots.knowledge import corpora, queries
from robots.knowledge.calculators import (
    atk_with_weapon,
    base_atk,
    flee,
    hit,
    matk_max,
    matk_min,
    soft_def,
    soft_mdef,
)

MAX_DECIDE_LINES = 6
MAX_ITEM_LINES = 3
MAX_MENTION_LINES = 3
MAX_LINE_CHARS = corpora.MAX_LINE_CHARS
_SELF_PREFIX = "self"


def _self_line(state: BotState, stats: tuple[int, ...]) -> str | None:
    """One bounded combat line from the received six stats (0x00BD order)."""
    if len(stats) != 6:
        return None
    str_, agi, vit, int_, dex, luk = stats
    batk = base_atk(str_, dex, luk)
    weapon_note = ""
    atk = batk
    for key in sorted(state.inventory, key=lambda k: (len(k), k))[:4]:
        try:
            item_id = int(key)
        except ValueError:
            continue
        fields = corpora.item_fields(item_id)
        if fields and str(fields.get("type", "")).lower() == "weapon":
            weapon_atk = corpora.item_weapon_attack(fields)
            if weapon_atk is not None:
                atk = atk_with_weapon(weapon_atk, str_, dex, luk)
                weapon_note = f" + {fields.get('name', 'weapon')} {weapon_atk}"
                break
    line = (
        f"{_SELF_PREFIX} (Lv {state.base_level}): atk {atk} (batk {batk}{weapon_note}), "
        f"matk {matk_min(int_)}-{matk_max(int_)}, hit {hit(state.base_level, dex)}, "
        f"flee {flee(state.base_level, agi)}, def2 {soft_def(vit)}, "
        f"mdef2 {soft_mdef(int_, vit)}"
    )
    return line[:MAX_LINE_CHARS]


def _inventory_lines(state: BotState, stats: tuple[int, ...] | None) -> list[str]:
    """Projection lines for up to three numeric inventory item ids."""
    stat_kwargs = None
    if stats and len(stats) == 6:
        stat_kwargs = {
            "str_": stats[0],
            "dex": stats[4],
            "luk": stats[5],
            "equip_atk": 0,
        }
    lines: list[str] = []
    for key in sorted(state.inventory, key=lambda k: (len(k), k)):
        try:
            item_id = int(key)
        except ValueError:
            continue
        line = corpora.item_projection_line(item_id, stats=stat_kwargs)
        if line is not None:
            lines.append(line)
        if len(lines) >= MAX_ITEM_LINES:
            break
    return lines


def _target_line(state: BotState) -> str | None:
    for actor in state.nearby:
        if actor.kind != "monster":
            continue
        fields = corpora.monster_fields(actor.name)
        if fields is not None:
            return corpora.monster_context_line(fields)
    return None


def _map_line(state: BotState) -> str | None:
    snippets = corpora.wiki_snippets(state.map_name, section="maps", limit=1)
    return f"{state.map_name}: {snippets[0]}"[:MAX_LINE_CHARS] if snippets else None


def _state_text_surfaces(state: BotState) -> tuple[str, ...]:
    """Free-text state surfaces a corpus name can appear in (chat, NPC pages)."""
    texts = [line.text for line in state.recent_chat[-3:]]
    dialog = state.npc_dialogue
    if dialog is not None:
        texts.extend(str(page) for page in dialog.pages[-2:])
    return tuple(texts)


def decide_knowledge_lines(state: BotState, *, topics: Sequence[str] = ()) -> list[str]:
    """The bounded knowledge bundle for one decide tick; [] when corpora lack it.

    ``topics`` carries the tick's free text worth mining for corpus names
    (objective/want wording the caller has at hand); recent chat and NPC
    pages are mined by default. Mention lines ride along last, inside the
    existing ``MAX_DECIDE_LINES`` cap.
    """
    lines: list[str] = []
    stats = state.received_stats
    if stats is not None:
        self_line = _self_line(state, stats)
        if self_line is not None:
            lines.append(self_line)
    lines.extend(_inventory_lines(state, stats))
    for candidate in (_target_line(state), _map_line(state)):
        if candidate is not None:
            lines.append(candidate)
    lines.extend(
        queries.mention_lines((*topics, *_state_text_surfaces(state)), max_lines=MAX_MENTION_LINES)
    )
    return lines[:MAX_DECIDE_LINES]
