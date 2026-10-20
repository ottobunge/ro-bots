"""Offline regressions against the pinned pre-re source, never a live DB."""

import re
from dataclasses import replace
from pathlib import Path

import pytest

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.mechanics_stub import StubMechanics
from robots.app.builds import BuildAuthor, author_build_from_template
from robots.domain.build import Build, CharacterSheet
from robots.domain.build_templates import PLAYSTYLE_TEMPLATES, BuildTemplate
from robots.society.models import Attitude, Playstyle, SocietyPersona

ROOT = Path(__file__).resolve().parents[1] / "rathena"


def test_paladin_path_has_source_required_rebirth():
    npc = (ROOT / "npc/jobs/2-2a/Paladin.txt").read_text()
    assert "Class == Job_Swordman_High" in npc
    assert template("tank-sac-paladin").class_path == (
        "Novice",
        "Swordsman",
        "Crusader",
        "High Novice",
        "High Swordsman",
        "Paladin",
    )


@pytest.mark.parametrize(
    ("playstyle", "first", "second"),
    [
        (Playstyle.TANK, "Swordsman", "Crusader"),
        (Playstyle.HEALER, "Acolyte", "Priest"),
        (Playstyle.MAGE, "Mage", "Wizard"),
        (Playstyle.HUNTER, "Archer", "Hunter"),
        (Playstyle.SUPPORT, "Archer", "Bard"),
        (Playstyle.MELEE, "Thief", "Assassin"),
    ],
)
def test_custom_fallback_cannot_skip_first_class(playstyle, first, second):
    source_first = "Swordman" if first == "Swordsman" else first
    tree = (ROOT / "db/pre-re/skill_tree.yml").read_text()
    job_block = tree.split(f"  - Job: {second}\n", 1)[1].split("  - Job:", 1)[0]
    assert f"      {source_first}: true" in job_block
    model = ScriptedDecisionModel(answers={"pick_template": {"choice": "custom"}})
    build = author_build_from_template(persona(playstyle), "Offline", (), model)
    assert build.class_path == ("Novice", first, second)


def test_swordsman_agi_cannot_change_to_assassin():
    model = ScriptedDecisionModel(
        answers={
            "class_path": {"choice": "Swordsman"},
            "stat_emphasis": {"choice": "agi"},
        }
    )
    build = BuildAuthor(model).author_build(
        persona(Playstyle.MELEE),
        "Offline",
        {"Swordsman": "fighter"},
        StubMechanics(),
    )
    assert build.class_path == ("Novice", "Swordsman", "Knight")


def item_row(name: str) -> str:
    text = (ROOT / "db/pre-re/item_db_equip.yml").read_text()
    rows = re.split(r"(?=^  - Id:)", text, flags=re.MULTILINE)
    return next(row for row in rows if f"    Name: {name}\n" in row)


@pytest.mark.parametrize(
    ("tid", "slot", "location", "job"),
    [
        ("tank-svd-knight", "accessory", "Both_Accessory", "Knight"),
        ("healer-battle-priest", "accessory", "Both_Accessory", "Priest"),
        ("mage-sage-bolter", "garment", "Garment", "Sage"),
        ("hunter-woe-trapper", "weapon", "Right_Hand", "Hunter"),
        ("support-battlesmith", "headgear", "Head_Top", "Blacksmith"),
        ("melee-crit-sin", "headgear", "Head_Top", "Assassin"),
    ],
)
def test_changed_equipment_exists_in_source_and_fits_job_slot(tid, slot, location, job):
    row = item_row(template(tid).equip_goals[slot])
    assert f"      {location}: true" in row
    if "    Jobs:\n" in row:
        assert f"      {job}: true" in row or "      All: true" in row
        assert f"      {job}: false" not in row
    if tid == "hunter-woe-trapper":
        assert "  - Id: 1207\n" in row


def test_battlesmith_cannot_pair_source_two_handed_buster_with_shield():
    t = template("support-battlesmith")
    assert "      Both_Hand: true" in item_row(t.equip_goals["weapon"])
    assert "shield" not in t.equip_goals


def source_skills(job: str) -> dict[str, tuple[int, dict[str, int]]]:
    text = (ROOT / "db/pre-re/skill_tree.yml").read_text()
    block = text.split(f"  - Job: {job}\n", 1)[1].split("  - Job:", 1)[0]
    rows = re.split(r"(?=^      - Name:)", block, flags=re.MULTILINE)[1:]
    result = {}
    for row in rows:
        code_match = re.search(r"^      - Name: (\w+)", row, re.MULTILINE)
        max_match = re.search(r"        MaxLevel: (\d+)", row)
        assert code_match is not None
        assert max_match is not None
        code = code_match[1]
        maximum = int(max_match[1])
        requires = {
            code: int(level)
            for code, level in re.findall(
                r"          - Name: (\w+)\n            Level: (\d+)",
                row,
            )
        }
        result[code] = (maximum, requires)
    return result


SKILL_CODES = {
    "Fire Bolt": "MG_FIREBOLT",
    "Fire Wall": "MG_FIREWALL",
    "Fire Ball": "MG_FIREBALL",
    "Sight": "MG_SIGHT",
    "Cold Bolt": "MG_COLDBOLT",
    "Frost Diver": "MG_FROSTDIVER",
    "Napalm Beat": "MG_NAPALMBEAT",
    "Lightning Bolt": "MG_LIGHTNINGBOLT",
    "Thunder Storm": "MG_THUNDERSTORM",
    "Stone Curse": "MG_STONECURSE",
    "Storm Gust": "WZ_STORMGUST",
    "Jupitel Thunder": "WZ_JUPITEL",
    "Lord of Vermilion": "WZ_VERMILION",
    "Meteor Storm": "WZ_METEOR",
    "Quagmire": "WZ_QUAGMIRE",
    "Sense": "WZ_ESTIMATION",
    "Sightrasher": "WZ_SIGHTRASHER",
    "Earth Spike": "WZ_EARTHSPIKE",
    "Heaven's Drive": "WZ_HEAVENDRIVE",
    "Mystical Amplification": "HW_MAGICPOWER",
    "Safety Wall": "MG_SAFETYWALL",
    "Adrenaline Rush": "BS_ADRENALINE",
    "Weapon Perfection": "BS_WEAPONPERFECT",
    "Over Thrust": "BS_OVERTHRUST",
    "Power Thrust": "BS_OVERTHRUST",
    "Hammer Fall": "BS_HAMMERFALL",
    "Weaponry Research": "BS_WEAPONRESEARCH",
    "Cart Revolution": "MC_CARTREVOLUTION",
    "Maximize Power": "BS_MAXIMIZE",
    "Hilt Binding": "BS_HILTBINDING",
}


def source_targets(t: BuildTemplate) -> list[tuple[str, int]]:
    return [
        (SKILL_CODES[name], int(level)) for name, level in (g.rsplit(" ", 1) for g in t.skill_goals)
    ]


@pytest.mark.parametrize(
    ("tid", "jobs", "expected_costs"),
    [
        ("mage-aoe-wizard", ("Mage", "Wizard"), (39, 49)),
        ("support-battlesmith", ("Merchant", "Blacksmith"), (1, 36)),
    ],
)
def test_bounded_skill_plans_are_source_legal_prerequisite_closed(tid, jobs, expected_costs):
    targets = source_targets(template(tid))
    levels = dict(targets)
    assert len(levels) == len(targets), "aliases must not allocate a skill twice"
    trees = [source_skills(job) for job in jobs]
    available = {code: row for tree in trees for code, row in tree.items()}
    for code, level in targets:
        assert code in available, code
        maximum, requires = available[code]
        assert 1 <= level <= maximum, code
        for ancestor, required_level in requires.items():
            assert levels.get(ancestor, 0) >= required_level, (code, ancestor, required_level)
    costs = tuple(sum(level for code, level in targets if code in tree) for tree in trees)
    assert costs == expected_costs
    assert all(cost <= 49 for cost in costs)


def test_sage_generic_elemental_change_not_authorable():
    assert "Elemental Change 1" not in template("mage-sage-bolter").skill_goals


def test_author_preserves_requested_levels_without_breaking_name_consumers():
    t = template("mage-aoe-wizard")
    build = author(t)
    assert build.skill_levels == {
        name: int(level) for name, level in (goal.rsplit(" ", 1) for goal in t.skill_goals)
    }
    assert "Storm Gust" in build.skill_goals
    assert build.validation_issues, "a plan must not imply complete executable validation"


def test_renewal_template_cannot_enter_classic_authoring():
    t = replace(template("mage-aoe-wizard"), ruleset="renewal")
    with pytest.raises(ValueError, match="ruleset"):
        author(t)


def test_skill_names_alone_do_not_certify_requested_level_progress():
    build = author(template("mage-aoe-wizard"))
    sheet = CharacterSheet(level=99, learned_skills=frozenset({"Storm Gust"}))
    assert sheet.progress_for(build).skills_learned == 0


def test_actual_learned_levels_are_compared_to_targets():
    build = author(template("mage-aoe-wizard"))
    sheet = CharacterSheet(level=99, skill_levels={"Storm Gust": 9, "Meteor Storm": 7})
    assert sheet.progress_for(build).skills_learned == 1


def test_catalog_does_not_claim_unsourced_market_prices():
    for rows in PLAYSTYLE_TEMPLATES.values():
        for t in rows:
            assert "prices:" not in t.notes.lower(), t.template_id
            assert "Prices unknown" in t.notes


def test_bard_notes_match_normal_attack_speed_buff():
    notes = template("support-woe-bard").notes
    assert "slows melee" not in notes
    assert "attack speed" in notes


def persona(playstyle: Playstyle = Playstyle.MAGE) -> SocietyPersona:
    return SocietyPersona(
        persona_id="classic",
        name="Classic",
        playstyle=playstyle,
        attitude=Attitude.GRINDER,
        chattiness=0.4,
        level_band=(30, 99),
    )


def template(template_id: str) -> BuildTemplate:
    return next(
        t for rows in PLAYSTYLE_TEMPLATES.values() for t in rows if t.template_id == template_id
    )


def author(t: BuildTemplate, score: int = 2) -> Build:
    model = ScriptedDecisionModel(
        answers={
            "pick_template": {"choice": t.template_id},
            "follow_closely": {"score": score},
        }
    )
    return author_build_from_template(persona(t.playstyle), "Offline", (t,), model)


def source_stat_cost(stats: dict[str, int]) -> int:
    pc = (ROOT / "src/map/pc.cpp").read_text()
    assert "#define PC_STATUS_POINT_COST(low) (( 1 + ((low) + 9) / 10 ))" in pc
    return sum(1 + (low + 9) // 10 for value in stats.values() for low in range(1, value))


def source_stat_budget() -> int:
    text = (ROOT / "db/pre-re/statpoint.yml").read_text()
    match = re.search(r"- Level: 99\n\s+Points: (\d+)", text)
    assert match is not None
    return int(match[1])


def test_wizard_adaptation_obeys_source_cap_and_nonlinear_budget():
    assert "max_parameter: 99" in (ROOT / "conf/battle/player.conf").read_text()
    build = author(template("mage-aoe-wizard"), 1)
    assert all(1 <= value <= 99 for value in build.stat_plan.values())
    assert source_stat_cost(build.stat_plan) <= source_stat_budget()


@pytest.mark.parametrize("stats", [{"INT": 100}, {"INT": 99, "DEX": 99, "VIT": 99}, {"INT": True}])
def test_author_rejects_unvalidated_or_illegal_stats(stats):
    t = replace(template("mage-aoe-wizard"), stat_plan=stats)
    with pytest.raises(ValueError, match="classic stat"):
        author(t)


@pytest.mark.parametrize("playstyle", list(Playstyle))
def test_every_catalog_stat_plan_fits_source_budget(playstyle):
    for t in PLAYSTYLE_TEMPLATES[playstyle]:
        assert source_stat_cost(t.stat_plan) <= source_stat_budget(), t.template_id
