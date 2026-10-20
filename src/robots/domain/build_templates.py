"""Curated classic (pre-renewal) build templates (ADR-009 addendum).

These are provisional Classic plans, not certified executable builds. Source
URLs retain provenance, not proof of ruleset validity. Level-99 base stats use
the pinned pre-re nonlinear cost and cap; damage/HP remain MechanicsPort
concerns. Only bounded skill closures are source checked; authoring explicitly
reports remaining prerequisites, acquisition and equipment validation gaps.
"""

from dataclasses import dataclass
from typing import final

from robots.society.models import Playstyle

# Slots a template may target (mirrors the equip cognition slot set).
KNOWN_SLOTS: frozenset[str] = frozenset(
    {"weapon", "shield", "headgear", "armor", "garment", "shoes", "accessory"}
)


@final
@dataclass(frozen=True, slots=True)
class BuildTemplate:
    """One curated pre-renewal build an agent can adopt at initialization."""

    template_id: str
    name: str
    playstyle: Playstyle
    class_path: tuple[str, ...]  # e.g. ("Novice", "Swordsman", "Knight")
    stat_plan: dict[str, int]  # base stat -> value at the ~99 cap
    skill_goals: tuple[str, ...]  # "Name Lv" entries, e.g. "Bash 10"
    equip_goals: dict[str, str]  # slot -> landmark item name
    milestones: tuple[int, ...]  # levels where the plan changes
    source_url: str
    notes: str
    ruleset: str = "classic"


_SRC_IRO_KNIGHT = "https://irowiki.org/classic/Knight"
_SRC_RMS_KNIGHT = (
    "https://write.ratemyserver.net/ragnoark-online-character-guides/dodgingbullets-knight-guide"
)
_SRC_IRO_PALADIN = "https://irowiki.org/classic/Paladin"
_SRC_RMS_PRIEST = (
    "https://write.ratemyserver.net/ragnoark-online-character-guides/heal-a-guide-to-priesting"
)
_SRC_GAMEFAQS_BPRIEST = "https://gamefaqs.gamespot.com/pc/561051-ragnarok-online/faqs/35120"
_SRC_ROC_WIZARD = "https://roclassic-guide.com/wizard-builds-for-pre-renewal-and-classic/"
_SRC_IRO_WIZARD = "https://irowiki.org/classic/Wizard"
_SRC_IRO_SAGE = "https://irowiki.org/wiki/Sage"
_SRC_IRO_HUNTER = "https://irowiki.org/classic/Hunter"
_SRC_ROC_HUNTER = "https://roclassic-guide.com/hunter-builds-for-pre-renewal-and-classic/"
_SRC_IRO_BARD = "https://irowiki.org/classic/Bard"
_SRC_IRO_BLACKSMITH = "https://irowiki.org/classic/Blacksmith"
_SRC_ROC_ASSASSIN = "https://roclassic-guide.com/assassin-builds-for-pre-renewal-and-classic"
_SRC_IRO_ASSASSIN = "https://irowiki.org/wiki/Assassin"

PLAYSTYLE_TEMPLATES: dict[Playstyle, tuple[BuildTemplate, ...]] = {
    Playstyle.TANK: (
        BuildTemplate(
            template_id="tank-svd-knight",
            name="SVD Knight",
            playstyle=Playstyle.TANK,
            class_path=("Novice", "Swordsman", "Knight"),
            stat_plan={"STR": 90, "VIT": 80, "DEX": 40},
            skill_goals=(
                "Bash 10",
                "Provoke 10",
                "Endure 5",
                "Spear Mastery 10",
                "Pierce 10",
                "Brandish Spear 10",
                "Spear Boomerang 5",
                "Riding 1",
                "Cavalier Mastery 5",
            ),
            equip_goals={
                "weapon": "Pike",
                "shield": "Mirror Shield",
                "headgear": "Iron Cain",
                "armor": "Coat",
                "garment": "Muffler",
                "shoes": "Shoes",
                "accessory": "Ring",
            },
            milestones=(45, 75, 99),
            source_url=_SRC_RMS_KNIGHT,
            notes=(
                "Classic STR/VIT/DEX vit-knight (RMS: Str ~84 base +8 job, Vit ~70 +10, "
                "Dex ~48 +6; iRO Classic SVD band STR 100+/VIT 80/DEX 45-60 incl. bonuses). "
                "Tanks and mobs with spear/shield; Pierce large mobs, Brandish for WoE. "
                "Milestones: 45 job change + Peco, 75 Brandish Spear online, 99 stat cap. "
                "Prices unknown: no server/date market evidence."
            ),
        ),
        BuildTemplate(
            template_id="tank-sac-paladin",
            name="Sacrifice / Shield Chain Paladin",
            playstyle=Playstyle.TANK,
            class_path=(
                "Novice",
                "Swordsman",
                "Crusader",
                "High Novice",
                "High Swordsman",
                "Paladin",
            ),
            stat_plan={"STR": 60, "VIT": 90, "INT": 20, "DEX": 40},
            skill_goals=(
                "Guard 5",
                "Shield Boomerang 5",
                "Rapid Smiting 5",
                "Shield Reflect 5",
                "Martyr's Reckoning 5",
                "Faith 10",
                "Sacrifice 5",
                "Endure 5",
                "Heal 5",
            ),
            equip_goals={
                "weapon": "Blade",
                "shield": "Cross Shield",
                "headgear": "Helm",
                "armor": "Full Plate",
                "garment": "Manteau",
                "shoes": "Boots",
                "accessory": "Rosary",
            },
            milestones=(45, 70, 99),
            source_url=_SRC_IRO_PALADIN,
            notes=(
                "iRO Classic 'Battle MR/RS' paladin: VIT 90-99, STR 60-80, DEX 30-70 — "
                "'the ultimate tank of the game' (Guard/Shield Reflect/Defending Aura + "
                "Martyr's Reckoning). Rapid Smiting (shield chain) needs Shield Boomerang 5. "
                "Milestones: 45 Crusader, 70 Paladin + shield skills, 99 Sacrifice pairs "
                "with the guild's wizard. Prices unknown: no server/date market evidence."
            ),
        ),
    ),
    Playstyle.HEALER: (
        BuildTemplate(
            template_id="healer-fs-priest",
            name="Full Support Priest",
            playstyle=Playstyle.HEALER,
            class_path=("Novice", "Acolyte", "Priest"),
            stat_plan={"INT": 90, "VIT": 80, "DEX": 40},
            skill_goals=(
                "Heal 10",
                "Blessing 10",
                "Increase AGI 10",
                "Kyrie Eleison 10",
                "Magnificat 5",
                "Angelus 5",
                "Resurrection 1",
                "Suffragium 3",
                "Status Recovery 1",
            ),
            equip_goals={
                "weapon": "Staff",
                "shield": "Guard",
                "headgear": "Circlet",
                "armor": "Silk Robe",
                "garment": "Muffler",
                "shoes": "Shoes",
                "accessory": "Heal Clip",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_RMS_PRIEST,
            notes=(
                "RMS support priest: 'basic build for a support priest is 80/80/80 "
                "(vit/int/dex)' — Vit tanks, Int heals, Dex cuts cast. Maxed Heal/Bless/AGI/"
                "Kyrie are the party staples. Milestones: 40 Priest job change, 70 core "
                "buffs maxed, 99 surviving WoE precasts. Prices unknown: no market evidence. "
                "Source uncertainty: the linked guide focuses on High Priest."
            ),
        ),
        BuildTemplate(
            template_id="healer-battle-priest",
            name="Battle Priest (mace)",
            playstyle=Playstyle.HEALER,
            class_path=("Novice", "Acolyte", "Priest"),
            stat_plan={"STR": 80, "AGI": 60, "VIT": 20, "INT": 20, "DEX": 30},
            skill_goals=(
                "Mace Mastery 10",
                "Blessing 10",
                "Increase AGI 10",
                "Kyrie Eleison 10",
                "Impositio Manus 5",
                "Gloria 5",
                "Magnificat 5",
                "Heal 5",
            ),
            equip_goals={
                "weapon": "Mace",
                "shield": "Guard",
                "headgear": "Circlet",
                "armor": "Saint's Robe",
                "garment": "Muffler",
                "shoes": "Sandals",
                "accessory": "Ring",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_GAMEFAQS_BPRIEST,
            notes=(
                "GameFAQs Battle Acolyte/Priest guide (CalxZinra): STR/AGI mace build, "
                "~25 INT for SP and Heal; fights solo with Kyrie up, still buffs a party. "
                "Milestones: 40 job change + Mace Mastery, 70 Kyrie/Impositio maxed, 99 "
                "solo grind. Prices unknown: no server/date market evidence."
            ),
        ),
    ),
    Playstyle.MAGE: (
        BuildTemplate(
            template_id="mage-aoe-wizard",
            name="INT/DEX AoE Wizard",
            playstyle=Playstyle.MAGE,
            class_path=("Novice", "Mage", "Wizard"),
            stat_plan={"INT": 99, "DEX": 99},
            skill_goals=(
                "Fire Bolt 10",
                "Fire Wall 10",
                "Storm Gust 10",
                "Jupitel Thunder 10",
                "Lord of Vermilion 10",
                "Meteor Storm 7",
                "Quagmire 5",
                "Sense 1",
                "Fire Ball 5",
                "Sight 1",
                "Cold Bolt 5",
                "Frost Diver 1",
                "Napalm Beat 1",
                "Lightning Bolt 4",
                "Thunder Storm 1",
                "Stone Curse 1",
                "Sightrasher 2",
                "Earth Spike 3",
                "Heaven's Drive 1",
            ),
            equip_goals={
                "weapon": "Arc Wand",
                "shield": "Guard",
                "headgear": "Apple of Archer",
                "armor": "Silk Robe",
                "garment": "Muffler",
                "shoes": "Shoes",
                "accessory": "Nimble Glove",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_ROC_WIZARD,
            notes=(
                "ROClassicGuide + iRO Classic: 'the most common wizard build is INT 99 "
                "then DEX 99' (r/RO pre-re: 99/99 int/dex, remainder VIT). AoE leveling "
                "with SG/MS/LoV; Firewall is the staple solo spell. Milestones: 40 Wizard "
                "job change, 70 AoE set online, 99 DEX gear. Prices unknown: no market evidence. "
                "Pinned prerequisite closure costs 39 Mage and 49 Wizard points at job 50."
            ),
        ),
        BuildTemplate(
            template_id="mage-sage-bolter",
            name="Bolter Sage (support/endow)",
            playstyle=Playstyle.MAGE,
            class_path=("Novice", "Mage", "Sage"),
            stat_plan={"INT": 90, "DEX": 70, "VIT": 50},
            skill_goals=(
                "Fire Bolt 10",
                "Lightning Bolt 10",
                "Study 10",
                "Cast Cancel 5",
                "Endow Blaze 5",
                "Heaven's Drive 5",
                "Dispell 5",
            ),
            equip_goals={
                "weapon": "Arc Wand",
                "shield": "Guard",
                "headgear": "Circlet",
                "armor": "Mage Coat",
                "garment": "Muffler",
                "shoes": "Shoes",
                "accessory": "Earring",
            },
            milestones=(40, 65, 99),
            source_url=_SRC_IRO_SAGE,
            notes=(
                "iRO Sage 'Basic Sage Leveling Build': VIT 60-80, INT 80-99, DEX 50-80, "
                "bolt spells for single target, endows 'indispensable' for other classes. "
                "Milestones: 40 Sage, 65 Endow for party support, 99 bolt spam. "
                "Prices unknown: no market evidence. Source uncertainty: linked guide is Renewal."
            ),
        ),
    ),
    Playstyle.HUNTER: (
        BuildTemplate(
            template_id="hunter-ds-blitzer",
            name="DEX/AGI Double Strafe Hunter",
            playstyle=Playstyle.HUNTER,
            class_path=("Novice", "Archer", "Hunter"),
            stat_plan={"AGI": 90, "DEX": 90, "INT": 20},
            skill_goals=(
                "Double Strafe 10",
                "Improve Concentration 10",
                "Owl's Eye 10",
                "Vulture's Eye 10",
                "Ankle Snare 5",
                "Blitz Beat 5",
                "Falconry Mastery 1",
                "Beast Bane 10",
            ),
            equip_goals={
                "weapon": "Gakkung",
                "headgear": "Apple of Archer",
                "armor": "Tights",
                "garment": "Muffler",
                "shoes": "Boots",
                "accessory": "Nimble Glove",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_IRO_HUNTER,
            notes=(
                "iRO Classic DEX/AGI 'PowerHouse' hunter: AGI 90-99 base, DEX 99 base "
                "(140-150 total) — DS for damage, falcon procs via LUK-less autocrit skip. "
                "No shield slot: bows are two-handed. Milestones: 40 Hunter + falcon, 70 "
                "DS/Concentration maxed, 99 dex-bonus chasing. Prices unknown: no market evidence."
            ),
        ),
        BuildTemplate(
            template_id="hunter-woe-trapper",
            name="INT/VIT Trapper (WoE)",
            playstyle=Playstyle.HUNTER,
            class_path=("Novice", "Archer", "Hunter"),
            stat_plan={"VIT": 70, "INT": 60, "DEX": 60},
            skill_goals=(
                "Ankle Snare 5",
                "Sandman 5",
                "Blast Mine 5",
                "Claymore Trap 5",
                "Land Mine 5",
                "Blitz Beat 5",
                "Falconry Mastery 1",
                "Spring Trap 5",
                "Detect 4",
                "Remove Trap 1",
            ),
            equip_goals={
                "weapon": "Main Gauche",
                "shield": "Guard",
                "headgear": "Apple of Archer",
                "armor": "Coat",
                "garment": "Muffler",
                "shoes": "Boots",
                "accessory": "Clip",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_ROC_HUNTER,
            notes=(
                "ROClassicGuide WoE trapper + iRO Classic DEX/INT trapper (VIT 70-80, "
                "INT 50-70): trap damage scales on DEX+INT, VIT keeps the trapper alive "
                "holding the line; dagger+shield allowed since traps don't need a bow. "
                "Milestones: 40 Hunter, 70 trap wall (Sandman/Ankle) online, 99 full "
                "trap tank. Main Gauche (1207) permits Guard. Prices unknown: no market evidence."
            ),
        ),
    ),
    Playstyle.SUPPORT: (
        BuildTemplate(
            template_id="support-woe-bard",
            name="Magic Strings WoE Bard",
            playstyle=Playstyle.SUPPORT,
            class_path=("Novice", "Archer", "Bard"),
            stat_plan={"DEX": 90, "VIT": 80, "INT": 25, "AGI": 20},
            skill_goals=(
                "Music Lessons 10",
                "Magic Strings 10",
                "Impressive Riff 10",
                "Melody Strike 5",
                "Encore 1",
                "Unchained Serenade 3",
                "Unbarring Octave 5",
                "Amp 1",
            ),
            equip_goals={
                "weapon": "Mandolin",
                "headgear": "Ghost Bandana",
                "armor": "Coat",
                "garment": "Muffler",
                "shoes": "Boots",
                "accessory": "Glove",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_IRO_BARD,
            notes=(
                "iRO Classic Bard WoE build: DEX 90, VIT 90, AGI 30, INT 25 — strings "
                "(Magic Strings) speed the guild wizard's casts; Impressive Riff increases "
                "normal attack speed. Milestones: 40 Bard, 70 Magic Strings 10, 99 VIT tank line. "
                "Prices unknown: no server/date market evidence. "
                "Ensembles need a Dancer partner; solo songs (Strings, Riff) carry it."
            ),
        ),
        BuildTemplate(
            template_id="support-battlesmith",
            name="Battlesmith buffer",
            playstyle=Playstyle.SUPPORT,
            class_path=("Novice", "Merchant", "Blacksmith"),
            stat_plan={"STR": 90, "AGI": 60, "VIT": 40, "DEX": 40},
            skill_goals=(
                "Adrenaline Rush 5",
                "Weapon Perfection 5",
                "Over Thrust 5",
                "Hilt Binding 1",
                "Hammer Fall 5",
                "Weaponry Research 10",
                "Cart Revolution 1",
                "Maximize Power 5",
            ),
            equip_goals={
                "weapon": "Buster",
                "headgear": "Bandana",
                "armor": "Chain Mail",
                "garment": "Manteau",
                "shoes": "Boots",
                "accessory": "Ring",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_IRO_BLACKSMITH,
            notes=(
                "iRO Classic Battlesmith stat build: STR 90-120, AGI 50-70, VIT 40+; "
                "party support comes from Adrenaline Rush/Weapon Perfection/Over Thrust "
                "buffs while hitting hard itself. Milestones: 40 Blacksmith, 70 AR+WP "
                "buff set, 99 Over Thrust damage. Prices unknown: no market evidence. "
                "Buster occupies both hands; Cart Revolution requires its quest."
            ),
        ),
    ),
    Playstyle.MELEE: (
        BuildTemplate(
            template_id="melee-crit-sin",
            name="Agi Crit Assassin (katar)",
            playstyle=Playstyle.MELEE,
            class_path=("Novice", "Thief", "Assassin"),
            stat_plan={"STR": 70, "AGI": 90, "DEX": 40, "LUK": 40},
            skill_goals=(
                "Katar Mastery 10",
                "Sonic Blow 10",
                "Cloaking 5",
                "Grimtooth 5",
                "Enchant Poison 5",
                "Double Attack 10",
                "Improve Dodge 10",
                "Hiding 5",
            ),
            equip_goals={
                "weapon": "Jur",
                "headgear": "Bandana",
                "armor": "Thief Clothes",
                "garment": "Muffler",
                "shoes": "Shoes",
                "accessory": "Brooch",
            },
            milestones=(40, 70, 99),
            source_url=_SRC_ROC_ASSASSIN,
            notes=(
                "ROClassicGuide 'Jur Crit Sin' + iRO equip-crit band (STR 60-90, AGI "
                "70-90, LUK ~40, DEX 40-60): crits never miss so LUK replaces DEX; "
                "Jur[3] with Soldier Skeleton cards. Milestones: 40 Assassin + katar "
                "mastery, 70 Sonic Blow/Grimtooth, 99 crit cap. Prices unknown: no market evidence."
            ),
        ),
        BuildTemplate(
            template_id="melee-agi-2h-knight",
            name="Two-Hand AGI Knight",
            playstyle=Playstyle.MELEE,
            class_path=("Novice", "Swordsman", "Knight"),
            stat_plan={"STR": 90, "AGI": 90, "DEX": 40, "VIT": 20},
            skill_goals=(
                "Twohand Quicken 10",
                "Bowling Bash 10",
                "Bash 10",
                "Provoke 10",
                "Magnum Break 5",
                "Two-Hand Sword Mastery 10",
                "Counter Attack 5",
                "Endure 5",
            ),
            equip_goals={
                "weapon": "Claymore",
                "headgear": "Iron Cain",
                "armor": "Coat",
                "garment": "Muffler",
                "shoes": "Boots",
                "accessory": "Ring",
            },
            milestones=(45, 75, 99),
            source_url=_SRC_IRO_KNIGHT,
            notes=(
                "iRO Classic 'AGI Two-Hand Sword' knight: STR 90-100, AGI 80-99 — high "
                "ASPD + Twohand Quicken, Bowling Bash for mobs, Counter Attack vs evasive "
                "foes. Milestones: 45 Knight + Peco, 75 Twohand Quicken/Bowling Bash, 99 "
                "aspd cap. Prices unknown: no server/date market evidence."
            ),
        ),
    ),
}


def validate_classic_stats(stats: dict[str, int]) -> None:
    """Validate level-99 normal-class endpoints, not per-level allocations.

    Pinned pre-re pc.cpp: PC_STATUS_POINT_COST(low) = 1 + (low + 9) / 10;
    statpoint.yml level 99 gives 1273; player.conf caps base stats at 99.
    Conservatively do not spend the extra transcendent points.
    """
    valid_names = {"STR", "AGI", "VIT", "INT", "DEX", "LUK"}
    if not stats or any(
        name.upper() not in valid_names or type(value) is not int or not 1 <= value <= 99
        for name, value in stats.items()
    ):
        msg = "invalid classic stat names or base-stat cap"
        raise ValueError(msg)
    cost = sum(1 + (low + 9) // 10 for value in stats.values() for low in range(1, value))
    if cost > 1273:
        msg = "classic stat plan exceeds validated level-99 budget"
        raise ValueError(msg)


def skill_name(goal: str) -> str:
    """'Bash 10' -> 'Bash' (the level is template metadata, not a skill id)."""
    return goal.rsplit(" ", 1)[0]
