"""Read-only rAthena base metadata, never server scripts or combat formulas.

Only explicitly selected ruleset files are read. No master Footer, custom
imports, combos, refine/card effects or server configuration is merged.
This catalog is deliberately not a mechanically complete equip/build validator.
"""

from collections.abc import Hashable
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from typing import final

import yaml
from yaml.nodes import MappingNode, Node

from robots.domain.build import ItemDigest, SkillDigest

# Pinned rAthena e985006: src/map/skill.hpp MAX_SKILL_LEVEL.
_MAX_SKILL_LEVEL = 13

_SKILL_KEYS = frozenset(
    [
        "Id",
        "Name",
        "Description",
        "MaxLevel",
        "Type",
        "TargetType",
        "DamageFlags",
        "Flags",
        "Range",
        "Hit",
        "HitCount",
        "Element",
        "SplashArea",
        "ActiveInstance",
        "Knockback",
        "GiveAp",
        "CopyFlags",
        "NoNearNPC",
        "CastCancel",
        "CastDefenseReduction",
        "CastTime",
        "AfterCastActDelay",
        "AfterCastWalkDelay",
        "Duration1",
        "Duration2",
        "Cooldown",
        "FixedCastTime",
        "CastTimeFlags",
        "CastDelayFlags",
        "Requires",
        "Unit",
        "Status",
    ]
)
_TREE_KEYS = frozenset(["Name", "MaxLevel", "Exclude", "BaseLevel", "JobLevel", "Requires"])

_ITEM_KEYS = frozenset(
    [
        "Id",
        "AegisName",
        "Name",
        "Type",
        "SubType",
        "Buy",
        "Sell",
        "Weight",
        "Attack",
        "MagicAttack",
        "Defense",
        "Range",
        "Slots",
        "Jobs",
        "Classes",
        "Gender",
        "Locations",
        "WeaponLevel",
        "ArmorLevel",
        "EquipLevelMin",
        "EquipLevelMax",
        "Refineable",
        "Gradable",
        "View",
        "AliasName",
        "Flags",
        "Delay",
        "Stack",
        "NoUse",
        "Trade",
        "Script",
        "EquipScript",
        "UnEquipScript",
    ]
)
_LOCATION_SLOTS = {
    "Right_Hand": "weapon",
    "Both_Hand": "weapon",
    "Left_Hand": "shield",
    "Armor": "armor",
    "Garment": "garment",
    "Shoes": "shoes",
    "Head_Top": "headgear",
    "Head_Mid": "headgear",
    "Head_Low": "headgear",
    "Both_Accessory": "accessory",
    "Right_Accessory": "accessory",
    "Left_Accessory": "accessory",
    "Costume_Head_Top": "costume_headgear",
    "Costume_Head_Mid": "costume_headgear",
    "Costume_Head_Low": "costume_headgear",
    "Costume_Garment": "costume_garment",
    "Shadow_Armor": "shadow_armor",
    "Shadow_Weapon": "shadow_weapon",
    "Shadow_Shield": "shadow_shield",
    "Shadow_Shoes": "shadow_shoes",
    "Shadow_Right_Accessory": "shadow_accessory",
    "Shadow_Left_Accessory": "shadow_accessory",
}
_CLASSES = frozenset(
    ["All", "Normal", "Upper", "Baby", "Third", "Third_Upper", "Third_Baby", "All_Third", "Fourth"]
)
_JOBS = frozenset(
    [
        "All",
        "Acolyte",
        "Alchemist",
        "Archer",
        "Assassin",
        "BardDancer",
        "Blacksmith",
        "Crusader",
        "Gunslinger",
        "Hunter",
        "KagerouOboro",
        "Knight",
        "Mage",
        "Merchant",
        "Monk",
        "Ninja",
        "Novice",
        "Priest",
        "Rebellion",
        "Rogue",
        "Sage",
        "SoulLinker",
        "Spirit_Handler",
        "StarGladiator",
        "Summoner",
        "SuperNovice",
        "Swordman",
        "Taekwon",
        "Thief",
        "Wizard",
    ]
)


class CatalogError(ValueError):
    """Invalid or unsupported catalog; no partial catalog is returned."""


def _fail(context: str) -> CatalogError:
    return CatalogError(f"Invalid or unsupported {context}")


_DUPLICATE_TRADE = object()


class _UniqueSafeLoader(yaml.SafeLoader):
    """Reject duplicate keys; quarantine item rows with duplicate opaque Trade."""

    def construct_mapping(self, node: Node, deep: bool = False) -> dict[Hashable, object]:
        if not isinstance(node, MappingNode):
            msg = "YAML mapping"
            raise _fail(msg)
        result: dict[Hashable, object] = {}
        for key_node, value_node in node.value:
            key: object = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                msg = "non-string YAML key"
                raise _fail(msg)
            if key in result:
                if key == "Trade" and any(k.value == "AegisName" for k, _ in node.value):
                    result[key] = _DUPLICATE_TRADE
                    continue
                msg = f"duplicate YAML key {key}"
                raise _fail(msg)
            result[key] = self.construct_object(value_node, deep=deep)
        return result


def _mapping(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise _fail(context)
    return dict(value)


def _rows(value: object, context: str) -> tuple[dict[str, object], ...]:
    if not isinstance(value, list):
        raise _fail(context)
    return tuple(_mapping(row, context) for row in value)


def _keys(row: dict[str, object], allowed: frozenset[str], context: str) -> None:
    if extra := row.keys() - allowed:
        msg = f"{context} keys: {sorted(extra)}"
        raise _fail(msg)


def _integer(value: object, context: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise _fail(context)
    return value


def _string(value: object, context: str) -> str:
    if not isinstance(value, str) or not value:
        raise _fail(context)
    return value


def _skill_level(value: object, context: str, minimum: int = 0) -> int:
    level = _integer(value, context, minimum)
    if level > _MAX_SKILL_LEVEL:
        raise _fail(context)
    return level


def _flags(
    value: object, context: str, allowed: frozenset[str] | None = None
) -> tuple[tuple[str, bool], ...]:
    row = _mapping(value, context)
    if allowed is not None:
        _keys(row, allowed, context)
    flags: list[tuple[str, bool]] = []
    for key, active in row.items():
        if type(active) is not bool:
            raise _fail(context)
        flags.append((key, active))
    return tuple(flags)


def _read(path: Path, kind: str, version: int) -> tuple[tuple[dict[str, object], ...], str]:
    raw = path.read_bytes()
    loader = _UniqueSafeLoader(raw)
    try:
        value: object = loader.get_single_data()
    except yaml.YAMLError as exc:
        msg = f"YAML in {path}"
        raise _fail(msg) from exc
    finally:
        loader.dispose()
    document = _mapping(value, str(path))
    _keys(document, frozenset({"Header", "Body", "Footer"}), str(path))
    header = _mapping(document.get("Header"), "Header")
    _keys(header, frozenset({"Type", "Version"}), "Header")
    if header.get("Type") != kind or _integer(header.get("Version"), "Version") != version:
        msg = f"Header for {kind} version {version}"
        raise _fail(msg)
    if "Footer" in document:
        msg = "Footer imports (explicit base files only)"
        raise _fail(msg)
    return _rows(document.get("Body"), "Body"), sha256(raw).hexdigest()


def _locations(row: dict[str, object]) -> tuple[str, tuple[str, ...]]:
    locations = tuple(
        sorted(
            key
            for key, active in _flags(
                row.get("Locations", {}), "Locations", frozenset(_LOCATION_SLOTS)
            )
            if active
        )
    )
    slots = {_LOCATION_SLOTS[location] for location in locations}
    if len(slots) == 1:
        return next(iter(slots)), locations
    return "multi-slot" if slots else "unplaced", locations


def _equip_levels(row: dict[str, object]) -> tuple[int, int | None]:
    minimum = _integer(row.get("EquipLevelMin", 0), "EquipLevelMin")
    maximum = _integer(row.get("EquipLevelMax", 0), "EquipLevelMax") or None
    if maximum is not None and maximum < minimum:
        msg = "EquipLevelMax below EquipLevelMin"
        raise _fail(msg)
    return minimum, maximum


def _permissions(
    row: dict[str, object], key: str, allowed: frozenset[str]
) -> tuple[tuple[str, bool], ...]:
    if key not in row:
        return (("All", True),)
    # A present null declaration has no active children, unlike an omitted mask.
    return _flags({} if row[key] is None else row[key], key, allowed)


def _gender(row: dict[str, object]) -> str:
    gender = _string(row.get("Gender", "Both"), "Gender")
    if gender not in {"Both", "Male", "Female"}:
        msg = "Gender"
        raise _fail(msg)
    return gender


def _unknown_scripts(row: dict[str, object]) -> tuple[str, ...]:
    unknown: list[str] = []
    for key in ("Script", "EquipScript", "UnEquipScript"):
        if row.get(key) is not None:
            _string(row[key], key)
            unknown.append(key)
    return (*unknown, "combo effects not loaded")


def _validate_item_identities(rows: tuple[dict[str, object], ...]) -> None:
    ids: set[int] = set()
    aegis_names: set[str] = set()
    for row in rows:
        item_id = _integer(row.get("Id"), "Id", 1)
        aegis = _string(row.get("AegisName"), "AegisName")
        if item_id in ids or aegis in aegis_names:
            msg = "duplicate item Id or AegisName"
            raise _fail(msg)
        ids.add(item_id)
        aegis_names.add(aegis)


def _item(row: dict[str, object], ruleset: str) -> ItemDigest | None:
    _keys(row, _ITEM_KEYS, "item")
    item_id = _integer(row.get("Id"), "Id", 1)
    name = _string(row.get("Name"), "Name")
    aegis = _string(row.get("AegisName"), "AegisName")
    kind = _string(row.get("Type"), "Type")
    if kind.lower() in {"petegg", "petarmor"} or row.get("Trade") is _DUPLICATE_TRADE:
        return None
    if kind not in {"Weapon", "Armor", "ShadowGear", "Shadowgear"}:
        msg = "player equipment Type"
        raise _fail(msg)
    effects = tuple(
        (stat, _integer(row.get(key, 0), key))
        for key, stat in (("Attack", "atk"), ("Defense", "def"), ("MagicAttack", "matk"))
    )
    slot, locations = _locations(row)
    minimum, maximum = _equip_levels(row)
    jobs = _permissions(row, "Jobs", _JOBS)
    classes = _permissions(row, "Classes", _CLASSES)
    gender = _gender(row)
    unknown = _unknown_scripts(row)
    text = (
        f"{name} [{aegis}, {item_id}, {ruleset}]: base metadata "
        f"{effects}; base level {minimum}..{maximum or 'unlimited'}; "
        f"locations {locations}; jobs {jobs}; classes {classes}; gender {gender}; "
        f"market price unknown; effects unknown: {', '.join(unknown)}; "
        "raw restriction masks; compatibility not evaluated; "
        "no character damage/defense calculation"
    )
    return ItemDigest(
        item_id=item_id,
        name=name,
        slot=slot,
        stat_effects=effects,
        required_level=minimum,
        price_tier=None,
        digest_text=text,
        aegis_name=aegis,
        ruleset=ruleset,
        locations=locations,
        jobs=jobs,
        classes=classes,
        gender=gender,
        maximum_level=maximum,
        card_slots=_integer(row.get("Slots", 0), "Slots"),
        unknown_effects=tuple(unknown),
    )


def _skill_index(rows: tuple[dict[str, object], ...]) -> dict[str, tuple[int, str, int]]:
    result: dict[str, tuple[int, str, int]] = {}
    ids: set[int] = set()
    for row in rows:
        _keys(row, _SKILL_KEYS, "skill")
        name = _string(row.get("Name"), "skill Name")
        skill_id = _integer(row.get("Id"), "skill Id", 1)
        if name in result or skill_id in ids:
            msg = "duplicate skill Name or Id"
            raise _fail(msg)
        ids.add(skill_id)
        result[name] = (
            skill_id,
            _string(row.get("Description"), "Description"),
            _skill_level(row.get("MaxLevel"), "skill MaxLevel", 1),
        )
    return result


def _tree_entry(
    row: dict[str, object], skills: dict[str, tuple[int, str, int]], cls: str, ruleset: str
) -> tuple[SkillDigest, bool]:
    _keys(row, _TREE_KEYS, "tree skill")
    name = _string(row.get("Name"), "tree Name")
    if name not in skills:
        msg = f"unknown tree skill {name}"
        raise _fail(msg)
    _, description, database_maximum = skills[name]
    maximum = min(_skill_level(row.get("MaxLevel"), "tree MaxLevel"), database_maximum)
    base = _integer(row.get("BaseLevel", 0), "BaseLevel")
    job = _integer(row.get("JobLevel", 0), "JobLevel")
    exclude = row.get("Exclude", False)
    if type(exclude) is not bool:
        msg = "Exclude"
        raise _fail(msg)
    prerequisites: dict[str, int] = {}
    for requirement in _rows(row.get("Requires", []), "tree Requires"):
        _keys(requirement, frozenset({"Name", "Level"}), "prerequisite")
        required = _string(requirement.get("Name"), "prerequisite Name")
        if required not in skills:
            msg = f"unknown prerequisite {required}"
            raise _fail(msg)
        level = min(
            _skill_level(requirement.get("Level"), "prerequisite Level"), skills[required][2]
        )
        if level:
            prerequisites[required] = level
        else:
            prerequisites.pop(required, None)
    needs = tuple(sorted(prerequisites.items()))
    text = (
        f"{name} ({description}) [{cls}, {ruleset}]: max {maximum} "
        f"(DB max {database_maximum}); declared base level {base}, job level {job}; "
        f"prerequisites {needs}; effects/formulas unknown; "
        "server job caps/configuration not applied; not a calculated learn level"
    )
    skill = SkillDigest(
        skill_id=name,
        name=description,
        required_level=base,
        digest_text=text,
        max_level=maximum,
        database_max_level=database_maximum,
        required_base_level=base,
        required_job_level=job,
        prerequisites=needs,
        class_name=cls,
        ruleset=ruleset,
        unknown_effects=(
            "effects/formulas",
            "casting requirements",
            "server job caps/configuration not applied",
        ),
    )
    return skill, exclude


def _own_trees(
    rows: tuple[dict[str, object], ...], skills: dict[str, tuple[int, str, int]], ruleset: str
) -> tuple[dict[str, dict[str, tuple[SkillDigest, bool]]], dict[str, tuple[tuple[str, bool], ...]]]:
    own: dict[str, dict[str, tuple[SkillDigest, bool]]] = {}
    parents: dict[str, tuple[tuple[str, bool], ...]] = {}
    for row in rows:
        _keys(row, frozenset({"Job", "Inherit", "Tree"}), "class tree")
        cls = _string(row.get("Job"), "Job")
        if cls in own:
            msg = "duplicate Job (custom patch trees not supported)"
            raise _fail(msg)
        own[cls] = {}
        parents[cls] = _flags(row.get("Inherit", {}), "Inherit")
        for entry in _rows(row.get("Tree", []), "Tree"):
            skill, excluded = _tree_entry(entry, skills, cls, ruleset)
            if skill.skill_id in own[cls]:
                msg = "duplicate tree skill (patch entries not supported)"
                raise _fail(msg)
            own[cls][skill.skill_id] = (skill, excluded)
    return own, parents


def _inherited_skills(
    cls: str,
    own: dict[str, dict[str, tuple[SkillDigest, bool]]],
    parents: dict[str, tuple[tuple[str, bool], ...]],
) -> dict[str, SkillDigest]:
    inherited: dict[str, SkillDigest] = {}
    for parent, active in parents[cls]:
        if parent not in own:
            msg = f"unknown inherited Job {parent}"
            raise _fail(msg)
        if active:
            inherited.update(
                (name, skill) for name, (skill, excluded) in own[parent].items() if not excluded
            )
    inherited.update((name, skill) for name, (skill, _) in own[cls].items())
    return inherited


def _trees(
    rows: tuple[dict[str, object], ...], skills: dict[str, tuple[int, str, int]], ruleset: str
) -> dict[str, tuple[SkillDigest, ...]]:
    own, parents = _own_trees(rows, skills, ruleset)
    result: dict[str, tuple[SkillDigest, ...]] = {}
    for cls in own:
        inherited = _inherited_skills(cls, own, parents)
        result[cls] = tuple(
            sorted(
                (
                    replace(
                        skill,
                        class_name=cls,
                        digest_text=skill.digest_text.replace(
                            f"[{skill.class_name}, ", f"[{cls}, "
                        ),
                    )
                    for skill in inherited.values()
                    if skill.max_level
                ),
                key=lambda skill: (
                    skill.required_level,
                    skill.required_job_level or 0,
                    skills[skill.skill_id][0],
                ),
            )
        )
    return result


def _selected_paths(db_root: Path, ruleset: str) -> tuple[Path, ...]:
    if ruleset not in {"pre-re", "re"}:
        msg = "ruleset (expected pre-re or re)"
        raise _fail(msg)
    selected = db_root.resolve() / ruleset
    paths = tuple(
        selected / filename for filename in ("item_db_equip.yml", "skill_db.yml", "skill_tree.yml")
    )
    if selected.resolve() != selected or any(path.resolve().parent != selected for path in paths):
        msg = "mixed ruleset or symlink import"
        raise _fail(msg)
    return paths


@final
class YamlMechanics:
    """Eager catalog scoped to ``db_root / ruleset``; no DB or server writes.

    Name lookup refuses ambiguous display names. Use ``item_by_id`` or
    ``item_by_aegis_name`` for an exact server identity instead.
    """

    def __init__(self, db_root: Path, *, ruleset: str) -> None:
        self.ruleset = ruleset
        paths = _selected_paths(db_root, ruleset)
        selected = paths[0].parent
        path = paths[0]
        rows, digest = _read(path, "ITEM_DB", 3)
        _validate_item_identities(rows)
        self.excluded_items = tuple(
            (_integer(row.get("Id"), "Id", 1), "duplicate Trade field")
            for row in rows
            if row.get("Trade") is _DUPLICATE_TRADE
        )
        items = [item for row in rows if (item := _item(row, ruleset)) is not None]
        self._by_id = {item.item_id: item for item in items}
        self._by_aegis = {item.aegis_name: item for item in items}

        self._items = tuple(sorted(items, key=lambda item: (item.required_level, item.item_id)))
        self._by_name: dict[str, tuple[ItemDigest, ...]] = {}
        for item in self._items:
            self._by_name[item.name] = (*self._by_name.get(item.name, ()), item)
        self.source_hashes: tuple[tuple[str, str], ...] = ((str(path), digest),)
        skill_rows, skill_hash = _read(selected / "skill_db.yml", "SKILL_DB", 4)
        tree_rows, tree_hash = _read(selected / "skill_tree.yml", "SKILL_TREE_DB", 1)
        self._skills = _trees(tree_rows, _skill_index(skill_rows), ruleset)
        self.source_hashes += (
            (str(selected / "skill_db.yml"), skill_hash),
            (str(selected / "skill_tree.yml"), tree_hash),
        )
        self.source_counts = (
            ("equipment_rows", len(rows)),
            ("player_equipment", len(items)),
            ("skill_rows", len(skill_rows)),
            ("class_trees", len(tree_rows)),
        )

    def skills_for_class(self, cls: str) -> tuple[SkillDigest, ...]:
        return self._skills.get("Swordman" if cls == "Swordsman" else cls, ())

    def item_by_name(self, name: str) -> ItemDigest | None:
        matches = self._by_name.get(name, ())
        return matches[0] if len(matches) == 1 else None

    def item_by_id(self, item_id: int) -> ItemDigest | None:
        return self._by_id.get(item_id)

    def item_by_aegis_name(self, aegis_name: str) -> ItemDigest | None:
        return self._by_aegis.get(aegis_name)

    def items_for_slot(self, slot: str) -> tuple[ItemDigest, ...]:
        return tuple(item for item in self._items if item.slot == slot)
