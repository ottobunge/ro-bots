"""Pre-renewal game-mechanics calculators, pure and offline.

Every function is a direct transcription of the PINNED rathena formulas
(submodule ``rathena/`` at e985006171d2); the docstrings cite
``rathena/src/map/status.cpp`` line numbers so the numbers stay auditable.
All inputs are integers and all arithmetic mirrors C integer semantics
(truncating division, double->uint32 truncation), so a projected value is the
value the server computes for the same inputs.
"""

from __future__ import annotations

from typing import Any


def max_hp(base_hp: int, vit: int, *, equip_vit: int = 0, hp_fix: int = 0) -> int:
    """Final max HP for a player.

    status.cpp:3511-3546 ``status_calc_maxhp_pc`` (call site 4353):
    ``dmax = job->base_hp[level-1]``; if vit: ``dmax *= 1.0 + vit*0.01``;
    "Vit from equip gives +1 additional HP"; plus additive bonuses. The caller
    passes the table value for the job at (level-1); the base table lives in
    ``db/pre-re/job_basepoints.yml`` (Novice Level 10 -> Hp 85).
    """
    value = float(base_hp)
    if vit > 0:
        value *= 1.0 + vit * 0.01
    value += equip_vit + hp_fix
    return int(value)


def max_sp(base_sp: int, int_: int, *, sp_fix: int = 0) -> int:
    """Final max SP for a player.

    status.cpp:3562-3590 ``status_calc_maxsp_pc`` (call site 4366):
    ``dmax = job->base_sp[level-1]; dmax *= 1.0 + int*0.01`` plus additive
    bonuses. The caller passes the table value for the job at (level-1);
    base table: ``db/pre-re/job_basepoints.yml`` (Novice group BaseSp
    Level 10 -> Sp 20).
    """
    value = float(base_sp)
    if int_ > 0:
        value *= 1.0 + int_ * 0.01
    value += sp_fix
    return int(value)


def base_atk(str_: int, dex: int, luk: int) -> int:
    """Base (bare-hand style) attack for a player, PRE-RENEWAL.

    status.cpp:2424-2495 ``status_base_atk``; the PRE-RENEWAL BL_PC branch
    (2486-2490) is ``dstr = str/10; str += dstr*dstr; str += dex/5 + luk/5``
    (integer division), capped at 2495.
    """
    dstr = str_ // 10
    value = str_ + dstr * dstr + dex // 5 + luk // 5
    return max(0, value)


def atk_with_weapon(weapon_atk: int, str_: int, dex: int, luk: int, *, equip_atk: int = 0) -> int:
    """Projected attack with a weapon: base ATK plus weapon ATK.

    PRE-RENEWAL the status block carries ``batk`` (status_base_atk) and the
    right-hand weapon ATK (``status->rhw.atk``, weapon + equip ATK from
    status.cpp:4390-4402); battle.cpp adds both for the base damage. The
    projection is the no-variance sum. Weapon ATK sources:
    ``db/pre-re/item_db_equip.yml`` (Knife [3] id 1201 -> Attack: 17).
    """
    return base_atk(str_, dex, luk) + weapon_atk + equip_atk


def matk_min(int_: int) -> int:
    """Minimum base magic attack, PRE-RENEWAL.

    status.cpp:2511-2513 ``status_base_matk_min``:
    ``int_ + (int_/7) * (int_/7)``.
    """
    return int_ + (int_ // 7) * (int_ // 7)


def matk_max(int_: int) -> int:
    """Maximum base magic attack, PRE-RENEWAL.

    status.cpp:2514-2516 ``status_base_matk_max``:
    ``int_ + (int_/5) * (int_/5)``.
    """
    return int_ + (int_ // 5) * (int_ // 5)


def aspd_pct(job_aspd_base: int, agi: int, dex: int, *, aspd_add: int = 0) -> float:
    """Displayed ASPD percentage for a player, PRE-RENEWAL.

    status.cpp:2403-2413 ``status_base_amotion_pc`` PRE-RENEWAL branch:
    ``amotion = job->aspd_base[weapon]``; ``amotion -= amotion*(4*agi+dex)/1000``;
    ``amotion += sd->bonus.aspd_add``. Displayed ASPD = 200 - amotion/10.
    Weapon bases: ``db/pre-re/job_aspd.yml`` (Novice group Dagger -> 650).
    """
    amotion = job_aspd_base
    amotion -= amotion * (4 * agi + dex) // 1000
    amotion += aspd_add
    return round(200 - amotion / 10, 1)


def hit(level: int, dex: int) -> int:
    """Hit value, PRE-RENEWAL: status.cpp:2704-2707 ``stat += level + dex``."""
    return max(1, level + dex)


def flee(level: int, agi: int) -> int:
    """Flee value, PRE-RENEWAL: status.cpp:2708-2711 ``stat += level + agi``."""
    return max(1, level + agi)


def soft_def(vit: int) -> int:
    """Soft (vit) defense, PRE-RENEWAL: status.cpp:2713-2715 ``def2 += vit``."""
    return max(0, vit)


def soft_mdef(int_: int, vit: int) -> int:
    """Soft magic defense, PRE-RENEWAL: status.cpp:2717-2719
    ``mdef2 += int_ + (vit / 2)``."""
    return max(0, int_ + vit // 2)


# ---- item-effect projection (criterion 4) ------------------------------------

_ETC_TYPES = {"etc", "misc", "delayconsume", "cash", "lifestaff?"}
_USABLE_TYPES = {"healing", "usable", "ammo"}
# Equipment kinds that never grant combat deltas by themselves.
_NO_BONUS_KIND = "misc"


def _first_int(raw: Any) -> int | None:
    """First integer in a field value: 8, "4 Z (4 Z)" -> 4, "--" -> None."""
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        digits = ""
        for char in raw:
            if char.isdigit():
                digits += char
            elif digits:
                break
        return int(digits) if digits else None
    return None


def _item_field(item: dict[str, Any], *names: str) -> Any:
    """Read a field under any of its known spellings (iro-db vs rathena keys)."""
    for name in names:
        if name in item and item[name] not in (None, "--"):
            return item[name]
    return None


def _item_kind(item: dict[str, Any]) -> str:
    raw = _item_field(item, "type", "Type")
    sub = _item_field(item, "subtype", "SubType")
    text = str(raw).strip().lower() if raw is not None else ""
    sub_text = str(sub).strip().lower() if sub is not None else ""
    if text == "weapon":
        return "weapon"
    # iro-db marks wearable gear as "Gear" (subtype Armor/Shield/Accessory...);
    # rathena marks it "Armor".
    if text in ("armor", "gear") or sub_text == "armor":
        return "armor"
    if text in _USABLE_TYPES:
        return "usable"
    if text in _ETC_TYPES:
        return _NO_BONUS_KIND
    return "unknown"


def _item_prices(item: dict[str, Any]) -> tuple[int | None, int | None]:
    buy = _first_int(_item_field(item, "buying_price", "Buy"))
    sell = _first_int(_item_field(item, "selling_price", "Sell"))
    if sell is None and buy is not None:
        sell = buy // 2  # rathena default sell value is half the buy value
    return buy, sell


def equip_projection(item: dict[str, Any], stats: dict[str, int] | None = None) -> dict[str, Any]:
    """Project what equipping/buying one item does to an agent.

    ``item`` is the parsed iro-db item fields (``entities.fields_json`` shape:
    ``type``/``subtype``/``attack``/``defense``/``buying_price``/
    ``selling_price``) or the equivalent rathena ``item_db.yml`` keys
    (``Type``/``Attack``/``Defense``/``Buy``/``Sell``). ``stats`` optionally
    carries the agent's ``str_``/``dex``/``luk`` so weapon rows also project
    the resulting attack (``atk_with_weapon``).

    Returns ``{"id", "name", "kind", "buy_price_z", "sell_price_z",
    "equip_delta", "projected_atk", "line"}``. ``line`` is the bounded
    decide-context form, e.g. ``"Chrysalis: sellable 4z; equip: no bonus
    (misc-class)"``.
    """
    kind = _item_kind(item)
    buy, sell = _item_prices(item)
    delta: dict[str, int] = {}
    projected_atk: int | None = None
    if kind == "weapon":
        weapon_atk = _first_int(_item_field(item, "attack", "Attack", "atk", "ATK"))
        if weapon_atk is not None:
            delta["atk"] = weapon_atk
            if stats:
                projected_atk = atk_with_weapon(
                    weapon_atk,
                    stats.get("str_", 0),
                    stats.get("dex", 0),
                    stats.get("luk", 0),
                    equip_atk=stats.get("equip_atk", 0),
                )
    elif kind == "armor":
        defense = _first_int(_item_field(item, "defense", "Defense", "def", "Def"))
        if defense is not None:
            delta["def"] = defense

    name = str(item.get("name") or item.get("Name") or item.get("AegisName") or "?")
    if delta:
        detail = ", ".join(f"{key} +{value}" for key, value in delta.items())
        if projected_atk is not None:
            detail += f" -> projected atk {projected_atk}"
    else:
        detail = "no bonus"
    sell_text = f"{sell}z" if sell is not None else "unsellable"
    line = f"{name}: sellable {sell_text}; equip: {detail} ({kind}-class)"
    return {
        "id": item.get("id"),
        "name": name,
        "kind": kind,
        "buy_price_z": buy,
        "sell_price_z": sell,
        "equip_delta": delta,
        "projected_atk": projected_atk,
        "line": line,
    }
