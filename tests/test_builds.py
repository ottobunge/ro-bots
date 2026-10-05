"""ADR-009: character builds + item cognition."""

import pytest

from robots.adapters.decision.stub import ScriptedDecisionModel
from robots.adapters.mechanics_stub import StubMechanics, YamlMechanics
from robots.app.builds import BuildAuthor, decide_item_action, note_build_progress
from robots.domain.build import Build, BuildProgress, CharacterSheet, ItemDigest
from robots.ports import MechanicsPort
from robots.society.memory import MemoryLog, StubSummarizer
from robots.society.models import Attitude, Playstyle, SocietyPersona


def make_persona(level_band: tuple[int, int] = (30, 60)) -> SocietyPersona:
    return SocietyPersona(
        persona_id="p1",
        name="Sable",
        playstyle=Playstyle.MELEE,
        attitude=Attitude.GRINDER,
        chattiness=0.4,
        level_band=level_band,
    )


ALLOWED = {"Swordsman": "Front-line fighter; fits melee/tank playstyles."}


def answer_build(class_path: str = "Swordsman", stat: str = "str", ambition: float = 2.0):
    return {
        "class_path": {"choice": class_path},
        "stat_emphasis": {"choice": stat},
        "equip_ambition": {"score": ambition},
    }


# -- StubMechanics ----------------------------------------------------------


def test_stub_mechanics_digests_deterministic_and_complete_sentences() -> None:
    m = StubMechanics()
    again = StubMechanics()
    for item in (*m.items_for_slot("weapon"), *m.items_for_slot("armor")):
        again_item = again.item_by_name(item.name)
        assert again_item is not None
        assert item.digest_text == again_item.digest_text
        assert "sells" in item.digest_text
        assert "lvl req" in item.digest_text


def test_stub_mechanics_satisfies_port_and_lookups() -> None:
    m = StubMechanics()
    assert isinstance(m, MechanicsPort)
    tsurugi = m.item_by_name("Tsurugi")
    assert tsurugi is not None
    assert tsurugi.stat_effects == (("atk", 90),)
    assert tsurugi.required_level == 40
    assert m.item_by_name("Mjolnir") is None
    weapons = m.items_for_slot("weapon")
    assert [i.name for i in weapons] == ["Sword", "Tsurugi", "Falchion"]
    assert len(m.skills_for_class("Swordsman")) == 3
    assert m.skills_for_class("Thief") == ()


def test_yaml_mechanics_refuses_without_new_dependency() -> None:
    y = YamlMechanics(item_db_path="rathena/db/item_db.yml")
    with pytest.raises(NotImplementedError):
        y.item_by_name("Sword")


# -- BuildAuthor ------------------------------------------------------------


def test_author_build_honors_allowed_classes_and_level_band() -> None:
    model = ScriptedDecisionModel(queue=[answer_build("Swordsman", "str", 2.0)])
    build = BuildAuthor(model).author_build(
        make_persona(), "Sable01", ALLOWED, StubMechanics(), build_id="b7"
    )
    assert build.class_path[1] in ALLOWED
    assert build.class_path == ("Novice", "Swordsman", "Knight")
    assert build.persona_id == "p1"
    assert build.char_name == "Sable01"
    assert build.stat_plan["str"] == 90
    assert build.skill_goals == ("Bash", "Increase HP Recovery", "Magnum Break")
    # min-maxed (tier 3): best reachable item per slot within level band max 60
    assert build.equip_goals["weapon"] == "Tsurugi"
    assert build.equip_goals["armor"] == "Saint's Armor"
    assert build.equip_goals["garment"] == "Saint's Cape"
    assert build.milestone_levels == (45, 60)
    assert model.calls == 1


def test_author_build_minimal_ambition_picks_cheap_items() -> None:
    model = ScriptedDecisionModel(queue=[answer_build("Swordsman", "vit", 0.0)])
    build = BuildAuthor(model).author_build(make_persona(), "Sable02", ALLOWED, StubMechanics())
    assert build.equip_goals["weapon"] == "Sword"  # tier<=0: only Sword qualifies for weapon
    assert build.equip_goals["armor"] == "Adventurer's Suit"
    assert build.class_path == ("Novice", "Swordsman", "Crusader")


def test_author_build_clamps_bad_answers_to_defaults() -> None:
    model = ScriptedDecisionModel(
        answers={
            "class_path": {"choice": "Wizard"},  # not allowed
            "stat_emphasis": {"choice": "luck"},  # not in playstyle list
            "equip_ambition": {"score": 99.0},
        }
    )
    build = BuildAuthor(model).author_build(make_persona(), "Sable03", ALLOWED, StubMechanics())
    assert "Swordsman" in build.class_path  # invalid 'Wizard' fell back to the only allowed class
    assert "str" in build.stat_plan


# -- decide_item_action -----------------------------------------------------


def make_item(name: str, atk: int, lvl: int) -> ItemDigest:
    return ItemDigest(
        item_id=9999,
        name=name,
        slot="weapon",
        stat_effects=(("atk", atk),),
        required_level=lvl,
        price_tier=1,
        digest_text=f"+{atk} ATK, lvl req {lvl}, sells ~100",
    )


def make_build(weapon_goal: str | None) -> Build:
    goals = {} if weapon_goal is None else {"weapon": weapon_goal}
    return Build(
        build_id="b1",
        persona_id="p1",
        char_name="Sable01",
        class_path=("Novice", "Swordsman", "Knight"),
        stat_plan={"str": 90},
        skill_goals=("Bash",),
        equip_goals=goals,
        milestone_levels=(45, 60),
    )


def test_decide_item_action_equip_when_new_beats_equipped() -> None:
    new = make_item("Tsurugi", 90, 40)
    equipped = make_item("Sword", 25, 2)
    model = ScriptedDecisionModel(queue=[{"item_action": {"choice": "equip"}}])
    action = decide_item_action({}, new, equipped, make_build("Tsurugi"), model)
    assert action == "equip"
    assert model.calls == 1


def test_decide_item_action_request_carries_digests_and_goal() -> None:
    captured: dict = {}

    class Recorder:
        def decide(self, request):
            captured.update(request)
            return {"answers": {"item_action": {"choice": "store"}}}

    new = make_item("Falchion", 52, 18)
    action = decide_item_action({}, new, None, make_build("Tsurugi"), Recorder())
    assert action == "store"
    assert captured["state"]["new_item"] == new.digest_text
    assert captured["state"]["build_goal_slot"] == "Tsurugi"
    assert "no item equipped" in captured["state"]["equipped_item"]
    assert set(captured["questions"]["item_action"]["criteria"]) == {
        "equip",
        "store",
        "sell",
        "discard",
    }


def test_decide_item_action_sell_when_no_goal_for_slot() -> None:
    new = make_item("Saint's Armor", 0, 45)
    model = ScriptedDecisionModel(queue=[{"item_action": {"choice": "sell"}}])
    action = decide_item_action({}, new, None, make_build("Tsurugi"), model)
    assert action == "sell"


def test_decide_item_action_criteria_text_matches_adr() -> None:
    seen: dict = {}

    class Recorder:
        def decide(self, request):
            seen.update(request["questions"]["item_action"]["criteria"])
            return {"answers": {"item_action": {"choice": "discard"}}}

    action = decide_item_action({}, make_item("X", 1, 1), None, make_build(None), Recorder())
    assert action == "discard"
    assert seen["equip"] == "Better than current and fits my build."
    assert seen["store"] == "Keep for later per my build plan."
    assert seen["sell"] == "No value to my build; convert to zeny."
    assert seen["discard"] == "Worthless."


# -- BuildProgress ----------------------------------------------------------


def test_build_progress_summary_counts_goals() -> None:
    build = make_build("Tsurugi")
    progress = BuildProgress(
        build=build,
        equip_met=("weapon",),
        equip_missed=("armor",),
        skills_learned=1,
        milestone_index=1,
    )
    assert progress.summary() == "build b1: equip 1/2, skills 1/1, milestone 1/2"


def test_character_sheet_progress() -> None:
    build = make_build("Tsurugi")
    sheet = CharacterSheet(
        level=60,  # both milestones (45, 60) reached
        learned_skills=frozenset({"Bash"}),
        equipped={"weapon": "Tsurugi"},
    )
    p = sheet.progress_for(build)
    assert p.equip_met == ("weapon",)
    assert p.skills_learned == 1
    assert p.milestone_index == 1
    assert "equip 1/1" in p.summary()


# -- note_build_progress ----------------------------------------------------


def test_note_build_progress_appends_experience_note() -> None:
    log = MemoryLog(StubSummarizer())
    build = make_build("Tsurugi")
    progress = BuildProgress(
        build=build,
        equip_met=(),
        equip_missed=("weapon",),
        skills_learned=0,
        milestone_index=0,
    )
    note_build_progress(log, progress)
    notes = log.notes()
    assert len(notes) == 1
    assert notes[0].kind == "other"
    assert notes[0].text == f"build: {progress.summary()}"
    assert notes[0].text.startswith("build: build b1")
