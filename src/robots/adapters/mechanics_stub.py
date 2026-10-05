"""Mechanics adapters (ADR-009): StubMechanics for tests, YamlMechanics skeleton.

The stub is authoritative for now: 8 deterministic items across slots with
plausible RO names and pre-calculated digests. ``YamlMechanics`` will parse
the repo's rAthena ``item_db.yml`` — deferred, no YAML dependency is added.
"""

from typing import ClassVar, final

from robots.domain.build import ItemDigest, SkillDigest


def _digest_text(
    stat_effects: tuple[tuple[str, int], ...], required_level: int, price_tier: int
) -> str:
    stats = ", ".join(f"{amount:+d} {stat.upper()}" for stat, amount in stat_effects) or "no stats"
    price = "~" + "0" * (price_tier + 3) if price_tier else "a few zeny"
    return f"{stats}, lvl req {required_level}, sells {price}"


@final
class StubMechanics:
    """In-memory MechanicsPort: 8 deterministic items, 3 classes of skills."""

    _ITEMS: tuple[ItemDigest, ...] = (
        ItemDigest(
            item_id=1101,
            name="Sword",
            slot="weapon",
            stat_effects=(("atk", 25),),
            required_level=2,
            price_tier=0,
            digest_text=_digest_text((("atk", 25),), 2, 0),
        ),
        ItemDigest(
            item_id=1113,
            name="Tsurugi",
            slot="weapon",
            stat_effects=(("atk", 90),),
            required_level=40,
            price_tier=2,
            digest_text=_digest_text((("atk", 90),), 40, 2),
        ),
        ItemDigest(
            item_id=1108,
            name="Falchion",
            slot="weapon",
            stat_effects=(("atk", 52),),
            required_level=18,
            price_tier=1,
            digest_text=_digest_text((("atk", 52),), 18, 1),
        ),
        ItemDigest(
            item_id=2307,
            name="Adventurer's Suit",
            slot="armor",
            stat_effects=(("def", 4),),
            required_level=2,
            price_tier=0,
            digest_text=_digest_text((("def", 4),), 2, 0),
        ),
        ItemDigest(
            item_id=2317,
            name="Saint's Armor",
            slot="armor",
            stat_effects=(("def", 10), ("int", 1)),
            required_level=45,
            price_tier=2,
            digest_text=_digest_text((("def", 10), ("int", 1)), 45, 2),
        ),
        ItemDigest(
            item_id=2503,
            name="Saint's Cape",
            slot="garment",
            stat_effects=(("def", 4), ("mdef", 10)),
            required_level=45,
            price_tier=2,
            digest_text=_digest_text((("def", 4), ("mdef", 10)), 45, 2),
        ),
        ItemDigest(
            item_id=2501,
            name="Hood",
            slot="garment",
            stat_effects=(("def", 2),),
            required_level=1,
            price_tier=0,
            digest_text=_digest_text((("def", 2),), 1, 0),
        ),
        ItemDigest(
            item_id=2403,
            name="Sandals",
            slot="shoes",
            stat_effects=(("def", 2), ("max_hp", 50)),
            required_level=3,
            price_tier=0,
            digest_text=_digest_text((("def", 2), ("max_hp", 50)), 3, 0),
        ),
    )

    _SKILLS: ClassVar[dict[str, tuple[SkillDigest, ...]]] = {
        "Swordsman": (
            SkillDigest("SM_BASH", "Bash", 2, "Bash: strong single hit, learn at lvl 2"),
            SkillDigest("SM_RECOVERY", "Increase HP Recovery", 4, "HP regen up, learn at lvl 4"),
            SkillDigest("SM_MAGNUM", "Magnum Break", 10, "Fire AoE around self, learn at lvl 10"),
        ),
        "Mage": (
            SkillDigest("MG_NAPALMBEAT", "Napalm Beat", 1, "Magic bolt, learn at lvl 1"),
            SkillDigest("MG_FIREBOLT", "Fire Bolt", 8, "Ranged fire magic, learn at lvl 8"),
            SkillDigest("MG_SAFETYWALL", "Safety Wall", 14, "Blocks melee hits, learn at lvl 14"),
        ),
        "Acolyte": (
            SkillDigest("AL_HEAL", "Heal", 3, "Restores HP, learn at lvl 3"),
            SkillDigest("AL_INCAGI", "Increase AGI", 6, "Party speed buff, learn at lvl 6"),
            SkillDigest("AL_BLESSING", "Blessing", 8, "Party INT/DEX buff, learn at lvl 8"),
        ),
    }

    def __init__(self) -> None:
        self._by_name: dict[str, ItemDigest] = {i.name: i for i in self._ITEMS}
        self._by_slot: dict[str, tuple[ItemDigest, ...]] = {}
        for item in self._ITEMS:
            self._by_slot[item.slot] = (*self._by_slot.get(item.slot, ()), item)

    def item_by_name(self, name: str) -> ItemDigest | None:
        return self._by_name.get(name)

    def items_for_slot(self, slot: str) -> tuple[ItemDigest, ...]:
        return self._by_slot.get(slot, ())

    def skills_for_class(self, cls: str) -> tuple[SkillDigest, ...]:
        return self._SKILLS.get(cls, ())


@final
class YamlMechanics:
    """MechanicsPort over rAthena ``item_db.yml`` / ``skill_db.yml`` (skeleton).

    Parses lazily on first use. The rAthena YAML dialect cannot be parsed with
    the stdlib, and the project carries no YAML dependency, so this adapter
    deliberately refuses at first use — :class:`StubMechanics` stays
    authoritative until that decision is made (ADR-009).
    """

    NOT_IMPLEMENTED_MSG = "YamlMechanics parsing is not implemented; use StubMechanics for now"

    def __init__(self, item_db_path: str, skill_db_path: str | None = None) -> None:
        self._item_db_path = item_db_path
        self._skill_db_path = skill_db_path
        self._loaded = False

    def _ensure_loaded(self) -> None:
        """Would read+parse the YAML files here; see the TODO in the class doc."""
        if not self._loaded:
            self._loaded = True
        # TODO(ADR-009): rAthena item_db.yml is a restricted YAML dialect; a
        # stdlib-only reader is nontrivial and no YAML dep will be added here
        # without a separate decision. StubMechanics stays authoritative.
        raise NotImplementedError(self.NOT_IMPLEMENTED_MSG)

    def item_by_name(self, name: str) -> ItemDigest | None:  # noqa: ARG002 (port signature)
        self._ensure_loaded()
        return None  # unreachable while parsing raises

    def items_for_slot(self, slot: str) -> tuple[ItemDigest, ...]:  # noqa: ARG002
        self._ensure_loaded()
        return ()  # unreachable while parsing raises

    def skills_for_class(self, cls: str) -> tuple[SkillDigest, ...]:  # noqa: ARG002
        self._ensure_loaded()
        return ()  # unreachable while parsing raises
